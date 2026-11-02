#pragma once

#include "CoreMinimal.h"

namespace WorldBalance
{
    inline constexpr float ClockExponent = 1.32192809489f;
    enum class EKind : uint8 { Production, Miner, Oil, Water, Belt, Lift, Generator, Storage };

    struct FBuilding
    {
        FString Id;
        FString ParentPath;
        FString RecipeName;
        FString Gate;
        EKind Kind;
        float Scale;
        float BasePower;
        int32 Outputs;
        bool RequireVanillaRecipe;
    };

    struct FMilestone
    {
        const TCHAR* Id;
        const TCHAR* Title;
        int32 Tier;
        int32 Cost;
    };

    WORLDBALANCE_API const TArray<FBuilding>& Buildings();
    WORLDBALANCE_API TConstArrayView<FMilestone> Milestones();
    WORLDBALANCE_API FString AssetPath(const TCHAR* Prefix, const FString& Id);
    WORLDBALANCE_API FString VanillaRecipePath(const FString& Name);
    WORLDBALANCE_API void RegisterVariablePowerClass(UClass* Class, float Density);
}
