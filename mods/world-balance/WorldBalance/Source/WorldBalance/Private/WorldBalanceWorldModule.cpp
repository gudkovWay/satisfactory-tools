#include "WorldBalanceWorldModule.h"
#include "WorldBalanceCatalog.h"
#include "FGGameState.h"
#include "FGRecipeManager.h"
#include "FGSchematicManager.h"
#include "Registry/ModContentRegistry.h"
#include "Engine/World.h"
#include "Buildables/FGBuildableManufacturerVariablePower.h"
#include "UObject/UnrealType.h"

DEFINE_LOG_CATEGORY_STATIC(LogWorldBalance, Log, All);

namespace
{
    template<class T> UClass* RequiredClass(const FString& Path)
    {
        UClass* Class = LoadClass<T>(nullptr, *Path);
        if (!Class) UE_LOG(LogWorldBalance, Fatal, TEXT("Required cooked asset missing: %s"), *Path);
        return Class;
    }
}

UWorldBalanceWorldModule::UWorldBalanceWorldModule()
{
    bRootModule = true;
}

void UWorldBalanceWorldModule::DispatchLifecycleEvent(ELifecyclePhase Phase)
{
    Super::DispatchLifecycleEvent(Phase);
    if (Phase == ELifecyclePhase::INITIALIZATION)
    {
        UModContentRegistry* Registry = UModContentRegistry::Get(this);
        if (!Registry) UE_LOG(LogWorldBalance, Fatal, TEXT("Mod content registry unavailable"));
        TArray<TPair<UClass*, UClass*>> ProductionClasses;
        for (const auto& Milestone : WorldBalance::Milestones())
        {
            UClass* Class = RequiredClass<UFGSchematic>(WorldBalance::AssetPath(TEXT("Schematic"), Milestone.Id));
            Registry->RegisterSchematic(TEXT("WorldBalance"), Class);
        }
        for (const auto& Row : WorldBalance::Buildings())
        {
            UClass* Recipe = RequiredClass<UFGRecipe>(WorldBalance::AssetPath(TEXT("Recipe"), Row.Id));
            UClass* Parent = RequiredClass<UFGRecipe>(WorldBalance::VanillaRecipePath(Row.RecipeName));
            UClass* Gate = Row.Gate.IsEmpty() ? nullptr : RequiredClass<UFGSchematic>(WorldBalance::AssetPath(TEXT("Schematic"), Row.Gate));
            Recipes.Add(Recipe);
            Parents.Add(Parent);
            Gates.Add(Gate);
            Registry->RegisterRecipe(TEXT("WorldBalance"), Recipe);
            if (Row.Kind == WorldBalance::EKind::Production)
            {
                UClass* Building = RequiredClass<AFGBuildable>(WorldBalance::AssetPath(TEXT("Build"), Row.Id));
                ProductionClasses.Emplace(RequiredClass<AFGBuildable>(Row.ParentPath), Building);
                if (Building->IsChildOf(AFGBuildableManufacturerVariablePower::StaticClass()))
                    WorldBalance::RegisterVariablePowerClass(Building, Row.Scale);
            }
        }
        // Explicit producer membership avoids relying on exact-class versus inheritance matching in recipe UIs.
        // Ingredient/product arrays and craft times remain untouched.
        for (const FGameObjectRegistration& Entry : Registry->GetRegisteredRecipes())
        {
            UClass* RecipeClass = Cast<UClass>(Entry.RegisteredObject);
            if (!RecipeClass || !RecipeClass->IsChildOf(UFGRecipe::StaticClass())) continue;
            UObject* CDO = RecipeClass->GetDefaultObject();
            FArrayProperty* Property = FindFProperty<FArrayProperty>(RecipeClass, TEXT("mProducedIn"));
            if (!Property) UE_LOG(LogWorldBalance, Fatal, TEXT("Recipe producer field unavailable"));
            auto& Producers = *Property->ContainerPtrToValuePtr<TArray<TSoftClassPtr<UObject>>>(CDO);
            const int32 OriginalCount = Producers.Num();
            for (int32 Index = 0; Index < OriginalCount; ++Index)
            {
                UClass* Producer = Producers[Index].LoadSynchronous();
                if (!Producer) continue;
                for (const auto& Pair : ProductionClasses)
                    if (Pair.Key->IsChildOf(Producer))
                        Producers.AddUnique(TSoftClassPtr<UObject>(Pair.Value));
            }
        }
    }
    else if (Phase == ELifecyclePhase::POST_INITIALIZATION)
    {
        AFGRecipeManager* RecipeManager = AFGRecipeManager::Get(GetWorld());
        AFGSchematicManager* SchematicManager = AFGSchematicManager::Get(GetWorld());
        if (!RecipeManager || !SchematicManager)
            UE_LOG(LogWorldBalance, Fatal, TEXT("Recipe or schematic manager unavailable"));
        RecipeManager->mOnRecipeAvailable.AddUniqueDynamic(this, &UWorldBalanceWorldModule::OnRecipeAvailable);
        SchematicManager->PurchasedSchematicDelegate.AddUniqueDynamic(this, &UWorldBalanceWorldModule::OnSchematicPurchased);
        if (AFGGameState* State = GetWorld()->GetGameState<AFGGameState>(); State && State->HasAuthority())
        {
            State->SetSpacePartsCostMultiplier(100.0f);
            State->SetEnergyCostMultiplier(1.0f);
            State->SetPartsCostMultiplier(1.0f);
            UClass* Starter = RequiredClass<UFGSchematic>(WorldBalance::AssetPath(TEXT("Schematic"), TEXT("Mining1")));
            if (!SchematicManager->IsSchematicPurchased(Starter))
                SchematicManager->GiveAccessToSchematic(Starter, nullptr,
                    ESchematicUnlockFlags::Force | ESchematicUnlockFlags::BlockTelemetry |
                    ESchematicUnlockFlags::SuppressNarrativeMessages);
        }
        RefreshAvailability();
    }
}

void UWorldBalanceWorldModule::OnRecipeAvailable(TSubclassOf<UFGRecipe>) { RefreshAvailability(); }
void UWorldBalanceWorldModule::OnSchematicPurchased(TSubclassOf<UFGSchematic>) { RefreshAvailability(); }

void UWorldBalanceWorldModule::RefreshAvailability()
{
    AFGRecipeManager* RecipeManager = AFGRecipeManager::Get(GetWorld());
    AFGSchematicManager* SchematicManager = AFGSchematicManager::Get(GetWorld());
    if (bRefreshing || !RecipeManager || !SchematicManager || !RecipeManager->HasAuthority()) return;
    TGuardValue<bool> Guard(bRefreshing, true);
    const auto& Rows = WorldBalance::Buildings();
    for (int32 Index = 0; Index < Rows.Num(); ++Index)
    {
        const bool GateOpen = !Gates[Index] || SchematicManager->IsSchematicPurchased(Gates[Index]);
        const bool ParentOpen = !Rows[Index].RequireVanillaRecipe || RecipeManager->IsRecipeAvailable(Parents[Index]);
        if (GateOpen && ParentOpen && !RecipeManager->IsRecipeAvailable(Recipes[Index]))
            RecipeManager->AddAvailableRecipe(Recipes[Index]);
    }
}
