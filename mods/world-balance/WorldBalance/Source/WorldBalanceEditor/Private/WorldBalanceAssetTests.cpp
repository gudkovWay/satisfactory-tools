#include "Misc/AutomationTest.h"
#include "WorldBalanceCatalog.h"
#include "Buildables/FGBuildable.h"
#include "Buildables/FGBuildableConveyorBase.h"
#include "Buildables/FGBuildableGeneratorFuel.h"
#include "Engine/BlueprintGeneratedClass.h"
#include "Engine/SCS_Node.h"
#include "Engine/SimpleConstructionScript.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "FGFactoryConnectionComponent.h"
#include "FGPipeConnectionComponent.h"
#include "FGRecipe.h"
#include "FGSchematic.h"
#include "Unlocks/FGUnlockBuildOverclock.h"
#include "Unlocks/FGUnlockRecipe.h"
#include "Resources/FGBuildingDescriptor.h"
#include "UObject/UnrealType.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWorldBalanceAssetContract, "WorldBalance.Assets.Contract",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWorldBalanceAssetContract::RunTest(const FString&)
{
    auto Number = [this](UObject* Object, const TCHAR* Name) -> double
    {
        FNumericProperty* Property = FindFProperty<FNumericProperty>(Object->GetClass(), Name);
        if (!TestNotNull(FString::Printf(TEXT("%s.%s"), *Object->GetName(), Name), Property)) return -1;
        const void* Address = Property->ContainerPtrToValuePtr<void>(Object);
        return Property->IsFloatingPoint() ? Property->GetFloatingPointPropertyValue(Address) : Property->GetSignedIntPropertyValue(Address);
    };
    for (const auto& Row : WorldBalance::Buildings())
    {
        UClass* Class = LoadClass<AFGBuildable>(nullptr, *WorldBalance::AssetPath(TEXT("Build"), Row.Id));
        UClass* Parent = LoadClass<AFGBuildable>(nullptr, *Row.ParentPath);
        UClass* Recipe = LoadClass<UFGRecipe>(nullptr, *WorldBalance::AssetPath(TEXT("Recipe"), Row.Id));
        if (!TestNotNull(Row.Id + TEXT(" buildable"), Class) || !TestNotNull(Row.Id + TEXT(" parent"), Parent) ||
            !TestNotNull(Row.Id + TEXT(" recipe"), Recipe)) continue;
        TestTrue(Row.Id + TEXT(" inherits original behavior"), Class->IsChildOf(Parent));
        UObject* CDO = Class->GetDefaultObject();
        UObject* Base = Parent->GetDefaultObject();
        const auto& Products = Recipe->GetDefaultObject<UFGRecipe>()->GetProducts();
        TestEqual(Row.Id + TEXT(" one build product"), Products.Num(), 1);
        if (Products.Num() == 1)
        {
            FClassProperty* BuildClass = FindFProperty<FClassProperty>(Products[0].ItemClass, TEXT("mBuildableClass"));
            if (TestNotNull(Row.Id + TEXT(" descriptor"), BuildClass))
                TestTrue(Row.Id + TEXT(" descriptor builds variant"), BuildClass->GetObjectPropertyValue_InContainer(Products[0].ItemClass->GetDefaultObject()) == Class);
        }
        if (Row.Id == TEXT("HadronCollider_D5"))
        {
            auto* Reference = CastChecked<UBlueprintGeneratedClass>(Parent);
            USCS_Node* MeshNode = nullptr;
            USCS_Node* PortNode = nullptr;
            for (USCS_Node* Node : Reference->SimpleConstructionScript->GetAllNodes())
            {
                if (Node->GetVariableName() == TEXT("SM_Output_01")) MeshNode = Node;
                if (Node->GetVariableName() == TEXT("Output0")) PortNode = Node;
            }
            if (TestNotNull(TEXT("vanilla outlet mesh reference"), MeshNode) &&
                TestNotNull(TEXT("vanilla outlet port reference"), PortNode))
            {
                TestTrue(TEXT("vanilla reference uses a common parent frame"),
                    MeshNode->GetParentComponentTemplate(Reference) == PortNode->GetParentComponentTemplate(Reference));
                const FTransform Mesh = CastChecked<USceneComponent>(MeshNode->ComponentTemplate)->GetRelativeTransform();
                const FTransform Port = CastChecked<USceneComponent>(PortNode->ComponentTemplate)->GetRelativeTransform();
                TestTrue(TEXT("outlet calibration matches vanilla geometry"),
                    Mesh.GetRelativeTransform(Port).Equals(
                        FTransform(FRotator(0, -90, 0), FVector(90, 0, -100)), 0.01));
            }
        }
        using enum WorldBalance::EKind;
        switch (Row.Kind)
        {
            case Production:
                TestEqual(Row.Id + TEXT(" cycle density"), Number(CDO, TEXT("mManufacturingSpeed")), Number(Base, TEXT("mManufacturingSpeed")) * Row.Scale);
                TestEqual(Row.Id + TEXT(" linear power density"), Number(CDO, TEXT("mPowerConsumption")), Number(Base, TEXT("mPowerConsumption")) * Row.Scale);
                break;
            case Miner:
                TestTrue(Row.Id + TEXT(" normal extraction rate"), FMath::IsNearlyEqual(Number(CDO, TEXT("mItemsPerCycle")) * 60 / Number(CDO, TEXT("mExtractCycleTime")), static_cast<double>(Row.Scale), 0.01));
                TestEqual(Row.Id + TEXT(" miner base MW"), Number(CDO, TEXT("mPowerConsumption")), static_cast<double>(Row.BasePower));
                break;
            case Oil:
            case Water:
                TestTrue(Row.Id + TEXT(" extraction scale"), FMath::IsNearlyEqual(Number(CDO, TEXT("mExtractCycleTime")) * Row.Scale, Number(Base, TEXT("mExtractCycleTime")), 0.001));
                TestEqual(Row.Id + TEXT(" extractor base MW"), Number(CDO, TEXT("mPowerConsumption")), static_cast<double>(Row.BasePower));
                break;
            case Belt:
            case Lift:
                TestEqual(Row.Id + TEXT(" items per minute"), Number(CDO, TEXT("mSpeed")) * 60 / AFGBuildableConveyorBase::ITEM_SPACING, static_cast<double>(Row.Scale));
                {
                    const FString Rate = FString::Printf(TEXT("%.0f resources per minute"), Row.Scale);
                    for (UObject* Described : {CDO, Products.Num() == 1 ? Products[0].ItemClass->GetDefaultObject() : nullptr})
                    {
                        if (!Described) continue;
                        FTextProperty* Description = FindFProperty<FTextProperty>(Described->GetClass(), TEXT("mDescription"));
                        if (TestNotNull(Row.Id + TEXT(" description field"), Description))
                            TestTrue(Row.Id + TEXT(" description matches transport capacity"),
                                Description->GetPropertyValue_InContainer(Described).ToString().Contains(Rate));
                    }
                }
                break;
            case Generator:
            {
                TestEqual(Row.Id + TEXT(" generator MW"), Number(CDO, TEXT("mPowerProduction")), Number(Base, TEXT("mPowerProduction")) * Row.Scale);
                auto* Fuel = Cast<AFGBuildableGeneratorFuel>(CDO);
                auto* BaseFuel = Cast<AFGBuildableGeneratorFuel>(Base);
                if (TestNotNull(Row.Id + TEXT(" native fuel behavior"), Fuel) && BaseFuel)
                {
                    TestTrue(Row.Id + TEXT(" unchanged fuel types"), Fuel->GetDefaultFuelClasses() == BaseFuel->GetDefaultFuelClasses());
                    TestTrue(Row.Id + TEXT(" unchanged supplemental type"), Fuel->GetSupplementalResourceClass() == BaseFuel->GetSupplementalResourceClass());
                    TestEqual(Row.Id + TEXT(" unchanged water per MW"), Number(CDO, TEXT("mSupplementalToPowerRatio")), Number(Base, TEXT("mSupplementalToPowerRatio")));
                }
                break;
            }
            case Storage:
                TestEqual(Row.Id + TEXT(" MWh"), Number(CDO, TEXT("mPowerStoreCapacity")), static_cast<double>(100 * Row.Scale));
                TestEqual(Row.Id + TEXT(" charge MW"), Number(CDO, TEXT("mPowerInputCapacity")), static_cast<double>(100 * Row.Scale));
                break;
        }
        if (Row.Kind != Belt && Row.Kind != Lift && Row.Kind != Storage)
        {
            TestEqual(Row.Id + TEXT(" base clock ceiling"), Number(CDO, TEXT("mMaxPotential")), 1.0);
            TestEqual(Row.Id + TEXT(" shard slots"), Number(CDO, TEXT("mPotentialShardSlots")), Row.Kind == Miner || Row.Kind == Oil ? 3.0 : 0.0);
            TestTrue(Row.Id + TEXT(" power exponent"), FMath::IsNearlyEqual(Number(CDO, TEXT("mPowerConsumptionExponent")), static_cast<double>(WorldBalance::ClockExponent), 0.000001));
            FBoolProperty* OverrideSlots = FindFProperty<FBoolProperty>(Class, TEXT("mOverridePotentialShardSlots"));
            if (TestNotNull(Row.Id + TEXT(" shard override field"), OverrideSlots))
                TestTrue(Row.Id + TEXT(" explicit shard slots"), OverrideSlots->GetPropertyValue_InContainer(CDO));
        }
        if (Row.Outputs > 1)
        {
            int32 Outputs = 0;
            int32 OutletMeshes = 0;
            TSet<FVector> Positions;
            for (UClass* Current = Class; Current; Current = Current->GetSuperClass())
            {
                UBlueprintGeneratedClass* BP = Cast<UBlueprintGeneratedClass>(Current);
                if (!BP || !BP->SimpleConstructionScript) continue;
                for (USCS_Node* Node : BP->SimpleConstructionScript->GetAllNodes())
                {
                    USceneComponent* Component = Cast<USceneComponent>(Node->ComponentTemplate);
                    const auto* Solid = Cast<UFGFactoryConnectionComponent>(Component);
                    const auto* Pipe = Cast<UFGPipeConnectionComponentBase>(Component);
                    if ((Solid && Solid->GetDirection() == EFactoryConnectionDirection::FCD_OUTPUT) ||
                        (Pipe && Pipe->GetPipeConnectionType() == EPipeConnectionType::PCT_PRODUCER))
                    { ++Outputs; Positions.Add(Component->GetRelativeLocation()); }
                    if (Row.Kind == Miner && Node->GetVariableName().ToString().StartsWith(TEXT("WB_Output")) && Solid)
                    {
                        for (USCS_Node* Child : Node->GetChildNodes())
                        {
                            auto* Mesh = Cast<UStaticMeshComponent>(Child->ComponentTemplate);
                            if (!Mesh) continue;
                            ++OutletMeshes;
                            if (TestNotNull(Row.Id + TEXT(" outlet mesh"), Mesh->GetStaticMesh().Get()))
                                TestEqual(Row.Id + TEXT(" vanilla outlet model"), Mesh->GetStaticMesh()->GetPathName(),
                                    FString(TEXT("/Game/FactoryGame/Buildable/Factory/FactoryInputs/Mesh/SM_Output_01.SM_Output_01")));
                            TestTrue(Row.Id + TEXT(" outlet mesh aligned to connection"),
                                Mesh->GetRelativeTransform().Equals(
                                    FTransform(FRotator(0, -90, 0), FVector(90, 0, -100)), 0.01));
                        }
                    }
                }
            }
            TestEqual(Row.Id + TEXT(" physical outlet count"), Outputs, Row.Outputs);
            TestEqual(Row.Id + TEXT(" separate outlet positions"), Positions.Num(), Row.Outputs);
            if (Row.Kind == Miner)
                TestEqual(Row.Id + TEXT(" one visual housing per added outlet"), OutletMeshes, Row.Outputs - 1);
        }
    }
    for (const auto& Row : WorldBalance::Milestones())
    {
        UClass* Class = LoadClass<UFGSchematic>(nullptr, *WorldBalance::AssetPath(TEXT("Schematic"), Row.Id));
        if (!TestNotNull(FString(Row.Id) + TEXT(" milestone"), Class)) continue;
        TestEqual(FString(Row.Id) + TEXT(" technology tier"), UFGSchematic::GetTechTier(Class), Row.Tier);
        TestTrue(FString(Row.Id) + TEXT(" HUB milestone"), UFGSchematic::GetType(Class) == ESchematicType::EST_Milestone);
        const auto Unlocks = UFGSchematic::GetUnlocks(Class);
        if (FString(Row.Id) == TEXT("Mining1"))
            TestTrue(TEXT("Mining I enables native overclocking"), Unlocks.ContainsByPredicate(
                [](UFGUnlock* Unlock) { return Unlock && Unlock->IsA<UFGUnlockBuildOverclock>(); }));
        if (FString(Row.Id) == TEXT("EarlyCoal"))
        {
            TArray<TSubclassOf<UFGRecipe>> Recipes;
            for (UFGUnlock* Unlock : Unlocks)
                if (auto* RecipeUnlock = Cast<UFGUnlockRecipe>(Unlock)) Recipes.Append(RecipeUnlock->GetRecipesToUnlock());
            for (const TCHAR* Name : {TEXT("Pipeline"), TEXT("PipeSupport"), TEXT("PipelineJunction_Cross"), TEXT("PipelinePump")})
            {
                UClass* Recipe = LoadClass<UFGRecipe>(nullptr, *WorldBalance::VanillaRecipePath(Name));
                TestTrue(FString(TEXT("Early coal unlocks ")) + Name, Recipe && Recipes.Contains(Recipe));
            }
        }
    }
    return !HasAnyErrors();
}
#endif
