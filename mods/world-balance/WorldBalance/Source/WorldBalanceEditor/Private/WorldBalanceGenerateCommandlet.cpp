#include "WorldBalanceGenerateCommandlet.h"
#include "WorldBalanceCatalog.h"
#include "WorldBalanceWorldModule.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Buildables/FGBuildable.h"
#include "Buildables/FGBuildableConveyorBase.h"
#include "Buildables/FGBuildableManufacturerVariablePower.h"
#include "Engine/Blueprint.h"
#include "Engine/BlueprintGeneratedClass.h"
#include "Engine/SCS_Node.h"
#include "Engine/SimpleConstructionScript.h"
#include "Engine/StaticMesh.h"
#include "Components/StaticMeshComponent.h"
#include "FGFactoryConnectionComponent.h"
#include "FGPipeConnectionFactory.h"
#include "FGRecipe.h"
#include "FGSchematic.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Misc/PackageName.h"
#include "Resources/FGBuildingDescriptor.h"
#include "UObject/SavePackage.h"
#include "UObject/UnrealType.h"
#include "Modules/ModuleManager.h"

DEFINE_LOG_CATEGORY_STATIC(LogWorldBalanceAuthoring, Log, All);
IMPLEMENT_MODULE(FDefaultModuleImpl, WorldBalanceEditor)

namespace
{
    double Number(UObject* Object, const TCHAR* Name)
    {
        FNumericProperty* Property = FindFProperty<FNumericProperty>(Object->GetClass(), Name);
        checkf(Property, TEXT("Numeric field %s missing on %s"), Name, *Object->GetPathName());
        const void* Value = Property->ContainerPtrToValuePtr<void>(Object);
        return Property->IsFloatingPoint() ? Property->GetFloatingPointPropertyValue(Value) : Property->GetSignedIntPropertyValue(Value);
    }

    void SetNumber(UObject* Object, const TCHAR* Name, double Value)
    {
        FNumericProperty* Property = FindFProperty<FNumericProperty>(Object->GetClass(), Name);
        checkf(Property, TEXT("Numeric field %s missing on %s"), Name, *Object->GetPathName());
        void* Address = Property->ContainerPtrToValuePtr<void>(Object);
        if (Property->IsFloatingPoint()) Property->SetFloatingPointPropertyValue(Address, Value);
        else Property->SetIntPropertyValue(Address, static_cast<int64>(Value));
    }

    void SetBool(UObject* Object, const TCHAR* Name, bool Value)
    {
        FBoolProperty* Property = FindFProperty<FBoolProperty>(Object->GetClass(), Name);
        checkf(Property, TEXT("Bool field %s missing on %s"), Name, *Object->GetPathName());
        Property->SetPropertyValue_InContainer(Object, Value);
    }

    void SetText(UObject* Object, const TCHAR* Name, const FString& Value)
    {
        FTextProperty* Property = FindFProperty<FTextProperty>(Object->GetClass(), Name);
        checkf(Property, TEXT("Text field %s missing on %s"), Name, *Object->GetPathName());
        Property->SetPropertyValue_InContainer(Object, FText::FromString(Value));
    }

    template<class T> T& Field(UObject* Object, const TCHAR* Name)
    {
        FProperty* Property = FindFProperty<FProperty>(Object->GetClass(), Name);
        checkf(Property, TEXT("Field %s missing on %s"), Name, *Object->GetPathName());
        return *Property->ContainerPtrToValuePtr<T>(Object);
    }

    UBlueprint* Create(const TCHAR* Prefix, const FString& Id, UClass* Parent)
    {
        check(Parent);
        const FString Name = FString(Prefix) + TEXT("_WB_") + Id;
        const FString PackageName = TEXT("/WorldBalance/Generated/") + Name;
        checkf(!FPackageName::DoesPackageExist(PackageName),
            TEXT("Generation requires an empty Generated directory; preserve the previous assets before regenerating %s"), *PackageName);
        UPackage* Package = CreatePackage(*PackageName);
        checkf(!FindObject<UObject>(Package, *Name), TEXT("Refusing to overwrite loaded generated asset: %s"), *Name);
        UBlueprint* BP = FKismetEditorUtilities::CreateBlueprint(Parent, Package, *Name, BPTYPE_Normal,
            UBlueprint::StaticClass(), UBlueprintGeneratedClass::StaticClass());
        check(BP);
        FAssetRegistryModule::AssetCreated(BP);
        return BP;
    }

    void Save(UBlueprint* BP)
    {
        check(BP->Status != BS_Error);
        BP->MarkPackageDirty();
        FSavePackageArgs Args;
        Args.TopLevelFlags = RF_Public | RF_Standalone;
        Args.SaveFlags = SAVE_None;
        const FString Filename = FPackageName::LongPackageNameToFilename(BP->GetOutermost()->GetName(), FPackageName::GetAssetPackageExtension());
        checkf(UPackage::SavePackage(BP->GetOutermost(), BP, *Filename, Args), TEXT("Cannot save %s"), *Filename);
    }

    TArray<USceneComponent*> ParentTemplates(UClass* Class)
    {
        TArray<USceneComponent*> Components;
        for (UClass* Current = Class; Current; Current = Current->GetSuperClass())
        {
            if (UBlueprintGeneratedClass* BPClass = Cast<UBlueprintGeneratedClass>(Current); BPClass && BPClass->SimpleConstructionScript)
                for (USCS_Node* Node : BPClass->SimpleConstructionScript->GetAllNodes())
                    if (USceneComponent* Component = Cast<USceneComponent>(Node->ComponentTemplate)) Components.Add(Component);
        }
        TInlineComponentArray<USceneComponent*> Native(CastChecked<AActor>(Class->GetDefaultObject()));
        for (USceneComponent* Component : Native) Components.AddUnique(Component);
        return Components;
    }

    void AddOutputs(UBlueprint* BP, const WorldBalance::FBuilding& Row)
    {
        if (Row.Outputs <= 1) return;
        const bool Fluid = Row.Kind == WorldBalance::EKind::Oil;
        USceneComponent* Source = nullptr;
        int32 Existing = 0;
        for (USceneComponent* Component : ParentTemplates(BP->ParentClass))
        {
            const auto* Solid = Cast<UFGFactoryConnectionComponent>(Component);
            const auto* Pipe = Cast<UFGPipeConnectionComponentBase>(Component);
            if ((!Fluid && Solid && Solid->GetDirection() == EFactoryConnectionDirection::FCD_OUTPUT) ||
                (Fluid && Pipe && Pipe->GetPipeConnectionType() == EPipeConnectionType::PCT_PRODUCER))
            { Source = Component; ++Existing; }
        }
        checkf(Source && Existing == 1, TEXT("Expected one inherited output on %s; found %d"), *Row.Id, Existing);
        USimpleConstructionScript* SCS = BP->SimpleConstructionScript;
        UStaticMesh* SocketMesh = LoadObject<UStaticMesh>(nullptr, Fluid ?
            TEXT("/Game/FactoryGame/Buildable/Factory/FactoryInputs/Mesh/SM_Pipe_InPut_01.SM_Pipe_InPut_01") :
            TEXT("/Game/FactoryGame/Buildable/Factory/FactoryInputs/Mesh/SM_Output_01.SM_Output_01"));
        checkf(SocketMesh, TEXT("Missing vanilla connector mesh for %s"), *Row.Id);
        for (int32 Index = 1; Index < Row.Outputs; ++Index)
        {
            USCS_Node* Node = SCS->CreateNode(Source->GetClass(), *FString::Printf(TEXT("WB_Output%d"), Index));
            // Copy the actual vanilla connection defaults, including fluid volume/pressure and connector clearance.
            for (TFieldIterator<FProperty> It(Source->GetClass()); It; ++It)
                if (It->HasAnyPropertyFlags(CPF_Edit) && !It->HasAnyPropertyFlags(CPF_Transient))
                    It->CopyCompleteValue_InContainer(Node->ComponentTemplate, Source);
            USceneComponent* Port = CastChecked<USceneComponent>(Node->ComponentTemplate);
            FVector Location = Source->GetRelativeLocation();
            // Vanilla outlets face +Y; keep every port on that face and spread along X.
            Location.X += (Index % 2 ? 1 : -1) * 200.0;
            Location.Z += ((Index - 1) / 2) * 200.0;
            Port->SetRelativeLocation(Location);
            Port->SetRelativeRotation(Source->GetRelativeRotation());
            SCS->AddNode(Node);
            USCS_Node* MeshNode = SCS->CreateNode(UStaticMeshComponent::StaticClass(),
                *FString::Printf(TEXT("WB_OutputMesh%d"), Index));
            UStaticMeshComponent* Mesh = CastChecked<UStaticMeshComponent>(MeshNode->ComponentTemplate);
            Mesh->SetStaticMesh(SocketMesh);
            Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            if (!Fluid)
            {
                // SM_Output_01 uses a floor pivot and +Y facing, unlike the connection's +X axis.
                // Matches the vanilla HadronCollider outlet mesh relative to Output0.
                Mesh->SetRelativeTransform(FTransform(FRotator(0, -90, 0), FVector(90, 0, -100)));
            }
            Node->AddChildNode(MeshNode);
        }
        FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);
        FKismetEditorUtilities::CompileBlueprint(BP);
        checkf(BP->Status != BS_Error, TEXT("Port construction failed: %s"), *Row.Id);
    }

    void ConfigureBuilding(UBlueprint* BP, const WorldBalance::FBuilding& Row)
    {
        UObject* CDO = BP->GeneratedClass->GetDefaultObject();
        UObject* Parent = BP->ParentClass->GetDefaultObject();
        using enum WorldBalance::EKind;
        if (Row.Kind == Belt || Row.Kind == Lift)
        {
            SetNumber(CDO, TEXT("mSpeed"), Row.Scale * AFGBuildableConveyorBase::ITEM_SPACING / 60.0);
            SetText(CDO, TEXT("mDescription"), FString::Printf(
                TEXT("Transports up to %.0f resources per minute.\nUsed to move resources %s."),
                Row.Scale, Row.Kind == Lift ? TEXT("vertically between buildings") : TEXT("between buildings")));
            return;
        }
        if (Row.Kind == Storage)
        {
            SetNumber(CDO, TEXT("mPowerStoreCapacity"), 100 * Row.Scale);
            SetNumber(CDO, TEXT("mPowerInputCapacity"), 100 * Row.Scale);
            return;
        }
        SetNumber(CDO, TEXT("mPowerConsumptionExponent"), WorldBalance::ClockExponent);
        const bool Extractor = Row.Kind == Miner || Row.Kind == Oil;
        SetNumber(CDO, TEXT("mMaxPotential"), 1);
        SetBool(CDO, TEXT("mOverridePotentialShardSlots"), true);
        SetNumber(CDO, TEXT("mPotentialShardSlots"), Extractor ? 3 : 0);
        if (Row.Kind == Production)
        {
            SetNumber(CDO, TEXT("mManufacturingSpeed"), Number(Parent, TEXT("mManufacturingSpeed")) * Row.Scale);
            SetNumber(CDO, TEXT("mPowerConsumption"), Number(Parent, TEXT("mPowerConsumption")) * Row.Scale);
            if (CDO->IsA<AFGBuildableManufacturerVariablePower>())
            {
                SetNumber(CDO, TEXT("mEstimatedMininumPowerConsumption"), Number(Parent, TEXT("mEstimatedMininumPowerConsumption")) * Row.Scale);
                SetNumber(CDO, TEXT("mEstimatedMaximumPowerConsumption"), Number(Parent, TEXT("mEstimatedMaximumPowerConsumption")) * Row.Scale);
            }
        }
        else if (Row.Kind == Generator)
            SetNumber(CDO, TEXT("mPowerProduction"), Number(Parent, TEXT("mPowerProduction")) * Row.Scale);
        else
        {
            SetNumber(CDO, TEXT("mPowerConsumption"), Row.BasePower);
            const double Items = Number(Parent, TEXT("mItemsPerCycle"));
            const double Cycle = Row.Kind == Miner ? Items * 60.0 / Row.Scale : Number(Parent, TEXT("mExtractCycleTime")) / Row.Scale;
            SetNumber(CDO, TEXT("mExtractCycleTime"), Cycle);
        }
    }

    TSubclassOf<UFGRecipe> GenerateBuilding(const WorldBalance::FBuilding& Row)
    {
        UClass* Parent = LoadClass<AFGBuildable>(nullptr, *Row.ParentPath);
        UClass* RecipeParent = LoadClass<UFGRecipe>(nullptr, *WorldBalance::VanillaRecipePath(Row.RecipeName));
        checkf(Parent && RecipeParent, TEXT("Missing vanilla assets for %s"), *Row.Id);
        const auto& Products = RecipeParent->GetDefaultObject<UFGRecipe>()->GetProducts();
        checkf(Products.Num() == 1 && Products[0].ItemClass->IsChildOf(UFGBuildingDescriptor::StaticClass()), TEXT("Invalid building recipe %s"), *Row.RecipeName);
        UBlueprint* Building = Create(TEXT("Build"), Row.Id, Parent);
        AddOutputs(Building, Row);
        ConfigureBuilding(Building, Row);
        SetText(Building->GeneratedClass->GetDefaultObject(), TEXT("mDisplayName"), TEXT("WB ") + Row.Id);
        Save(Building);

        UBlueprint* Descriptor = Create(TEXT("Desc"), Row.Id, Products[0].ItemClass);
        Field<TSubclassOf<AFGBuildable>>(Descriptor->GeneratedClass->GetDefaultObject(), TEXT("mBuildableClass")) = Building->GeneratedClass.Get();
        if (Row.Kind == WorldBalance::EKind::Belt || Row.Kind == WorldBalance::EKind::Lift)
            SetText(Descriptor->GeneratedClass->GetDefaultObject(), TEXT("mDescription"),
                Field<FText>(Building->GeneratedClass->GetDefaultObject(), TEXT("mDescription")).ToString());
        Save(Descriptor);
        UBlueprint* Recipe = Create(TEXT("Recipe"), Row.Id, RecipeParent);
        UObject* RecipeCDO = Recipe->GeneratedClass->GetDefaultObject();
        Field<TArray<FItemAmount>>(RecipeCDO, TEXT("mProduct")) = {FItemAmount(Descriptor->GeneratedClass.Get(), 1)};
        if (Row.Id == TEXT("Miner2") || Row.Id == TEXT("Miner3"))
        {
            auto Item = [](const TCHAR* Folder, const TCHAR* Name, int32 Count)
            {
                const FString Path = FString::Printf(TEXT("/Game/FactoryGame/Resource/Parts/%s/%s.%s_C"), Folder, Name, Name);
                UClass* Class = LoadClass<UFGItemDescriptor>(nullptr, *Path);
                checkf(Class, TEXT("Missing construction ingredient %s"), *Path);
                return FItemAmount(Class, Count);
            };
            auto& Cost = Field<TArray<FItemAmount>>(RecipeCDO, TEXT("mIngredients"));
            // Miner II is a steel-tier machine; Miner III must not require the late vanilla Mk.3 components.
            Cost = Row.Id == TEXT("Miner2") ? TArray<FItemAmount>{Item(TEXT("ModularFrame"), TEXT("Desc_ModularFrame"), 10),
                Item(TEXT("Rotor"), TEXT("Desc_Rotor"), 10), Item(TEXT("SteelPipe"), TEXT("Desc_SteelPipe"), 40)} :
                TArray<FItemAmount>{Item(TEXT("ModularFrame"), TEXT("Desc_ModularFrame"), 20),
                Item(TEXT("Motor"), TEXT("Desc_Motor"), 20), Item(TEXT("SteelPipe"), TEXT("Desc_SteelPipe"), 100),
                Item(TEXT("SteelPlateReinforced"), TEXT("Desc_SteelPlateReinforced"), 50)};
        }
        Save(Recipe);
        return Recipe->GeneratedClass.Get();
    }

    void GenerateMilestone(const WorldBalance::FMilestone& Row)
    {
        UBlueprint* BP = Create(TEXT("Schematic"), Row.Id, UFGSchematic::StaticClass());
        UObject* CDO = BP->GeneratedClass->GetDefaultObject();
        Field<ESchematicType>(CDO, TEXT("mType")) = ESchematicType::EST_Milestone;
        SetText(CDO, TEXT("mDisplayName"), Row.Title);
        SetText(CDO, TEXT("mDescription"), TEXT("Unlocks the named World Balance class. Production variants still require the original building technology. Recipes retain vanilla material ratios."));
        SetNumber(CDO, TEXT("mTechTier"), Row.Tier);
        SetNumber(CDO, TEXT("mTimeToComplete"), 30);
        UClass* Plates = LoadClass<UFGItemDescriptor>(nullptr, TEXT("/Game/FactoryGame/Resource/Parts/IronPlate/Desc_IronPlate.Desc_IronPlate_C"));
        UClass* Cable = LoadClass<UFGItemDescriptor>(nullptr, TEXT("/Game/FactoryGame/Resource/Parts/Cable/Desc_Cable.Desc_Cable_C"));
        check(Plates && Cable);
        Field<TArray<FItemAmount>>(CDO, TEXT("mCost")) = {FItemAmount(Plates, Row.Cost), FItemAmount(Cable, Row.Cost / 2)};
        if (FString(Row.Id) == TEXT("Mining1"))
            Field<TArray<TObjectPtr<UFGUnlock>>>(CDO, TEXT("mUnlocks")).Add(
                NewObject<UWBOverclockUnlock>(CDO, TEXT("ExtractionOverclocking"), RF_Transactional));
        if (FString(Row.Id) == TEXT("EarlyCoal"))
        {
            UWBRecipeUnlock* Unlock = NewObject<UWBRecipeUnlock>(CDO, TEXT("EarlyFluidInfrastructure"), RF_Transactional);
            for (const TCHAR* Name : {TEXT("Pipeline"), TEXT("PipeSupport"), TEXT("PipelineJunction_Cross"), TEXT("PipelinePump")})
            {
                UClass* Recipe = LoadClass<UFGRecipe>(nullptr, *WorldBalance::VanillaRecipePath(Name));
                check(Recipe);
                Unlock->AddRecipe(Recipe);
            }
            Field<TArray<TObjectPtr<UFGUnlock>>>(CDO, TEXT("mUnlocks")).Add(Unlock);
        }
        Save(BP);
    }
}

UWorldBalanceGenerateCommandlet::UWorldBalanceGenerateCommandlet()
{
    IsClient = false;
    IsServer = false;
    IsEditor = true;
    LogToConsole = true;
}

int32 UWorldBalanceGenerateCommandlet::Main(const FString& Params)
{
    if (Params.Contains(TEXT("Inspect")))
    {
        for (const auto& Row : WorldBalance::Buildings())
        {
            UClass* Parent = LoadClass<AFGBuildable>(nullptr, *Row.ParentPath);
            if (!Parent) { UE_LOG(LogWorldBalanceAuthoring, Error, TEXT("Missing %s"), *Row.ParentPath); return 1; }
            for (USceneComponent* Component : ParentTemplates(Parent))
            {
                if (Row.Outputs > 1 || Row.Id == TEXT("HadronCollider_D5"))
                    UE_LOG(LogWorldBalanceAuthoring, Display, TEXT("%s: %s [%s] transform %s"), *Row.Id,
                        *Component->GetName(), *Component->GetClass()->GetName(), *Component->GetRelativeTransform().ToString());
                if (const auto* Mesh = Cast<UStaticMeshComponent>(Component); Mesh && Mesh->GetStaticMesh() &&
                    Mesh->GetStaticMesh()->GetName().Contains(TEXT("Output")))
                    UE_LOG(LogWorldBalanceAuthoring, Display, TEXT("Output mesh reference %s %s: %s transform %s bounds %s"),
                        *Row.Id, *Mesh->GetName(), *Mesh->GetStaticMesh()->GetPathName(),
                        *Mesh->GetRelativeTransform().ToString(), *Mesh->GetStaticMesh()->GetBoundingBox().ToString());
            }
        }
        UStaticMesh* Output = LoadObject<UStaticMesh>(nullptr,
            TEXT("/Game/FactoryGame/Buildable/Factory/FactoryInputs/Mesh/SM_Output_01.SM_Output_01"));
        check(Output);
        UE_LOG(LogWorldBalanceAuthoring, Display, TEXT("Standalone output mesh bounds %s"), *Output->GetBoundingBox().ToString());
        return 0;
    }
    for (const auto& Row : WorldBalance::Buildings()) GenerateBuilding(Row);
    for (const auto& Row : WorldBalance::Milestones()) GenerateMilestone(Row);
    UE_LOG(LogWorldBalanceAuthoring, Display, TEXT("Generated %d building families and %d milestones"),
        WorldBalance::Buildings().Num(), WorldBalance::Milestones().Num());
    return 0;
}
