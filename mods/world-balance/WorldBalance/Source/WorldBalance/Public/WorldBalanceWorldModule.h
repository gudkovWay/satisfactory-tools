#pragma once

#include "CoreMinimal.h"
#include "Module/GameWorldModule.h"
#include "Unlocks/FGUnlockRecipe.h"
#include "Unlocks/FGUnlockBuildOverclock.h"
#include "WorldBalanceWorldModule.generated.h"

UCLASS()
class WORLDBALANCE_API UWBRecipeUnlock : public UFGUnlockRecipe
{
    GENERATED_BODY()
};

UCLASS()
class WORLDBALANCE_API UWBOverclockUnlock : public UFGUnlockBuildOverclock
{
    GENERATED_BODY()
};

UCLASS()
class WORLDBALANCE_API UWorldBalanceWorldModule : public UGameWorldModule
{
    GENERATED_BODY()
public:
    UWorldBalanceWorldModule();
    virtual void DispatchLifecycleEvent(ELifecyclePhase Phase) override;
private:
    UFUNCTION() void OnRecipeAvailable(TSubclassOf<UFGRecipe> Recipe);
    UFUNCTION() void OnSchematicPurchased(TSubclassOf<class UFGSchematic> Schematic);
    void RefreshAvailability();
    UPROPERTY() TArray<TSubclassOf<UFGRecipe>> Recipes;
    UPROPERTY() TArray<TSubclassOf<UFGRecipe>> Parents;
    UPROPERTY() TArray<TSubclassOf<class UFGSchematic>> Gates;
    bool bRefreshing = false;
};
