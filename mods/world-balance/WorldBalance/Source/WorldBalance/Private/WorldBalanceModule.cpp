#include "Modules/ModuleManager.h"
#include "WorldBalanceCatalog.h"
#include "WorldBalanceInventory.h"
#include "Buildables/FGBuildableFactory.h"
#include "Buildables/FGBuildableManufacturerVariablePower.h"
#include "Buildables/FGBuildableResourceExtractor.h"
#include "FGFactoryConnectionComponent.h"
#include "Patching/NativeHookManager.h"
#include "UObject/UObjectGlobals.h"
#include "UObject/UnrealType.h"

namespace
{
    TMap<TWeakObjectPtr<const UClass>, float> VariablePowerClasses;
    float Density(const UObject* Object)
    {
        const float* Value = VariablePowerClasses.Find(Object->GetClass());
        return Value ? *Value : 1.0f;
    }
}

void WorldBalance::RegisterVariablePowerClass(UClass* Class, float Value)
{
    check(IsInGameThread());
    VariablePowerClasses.Add(Class, Value);
}

class FWorldBalanceModule final : public IModuleInterface
{
public:
    virtual void StartupModule() override
    {
#if !WITH_EDITOR
        // Variable-power recipes define their own constant/range; changing the building's fixed MW is insufficient.
        PowerHook = SUBSCRIBE_METHOD_VIRTUAL(AFGBuildableManufacturerVariablePower::GetProducingPowerConsumptionBase,
            GetMutableDefault<AFGBuildableManufacturerVariablePower>(),
            [](auto& Scope, const AFGBuildableManufacturerVariablePower* Self)
            { const float D = Density(Self); if (D != 1.0f) Scope.Override(Scope(Self) * D); });
        MinHook = SUBSCRIBE_METHOD(AFGBuildableManufacturerVariablePower::GetMinPowerConsumption,
            [](auto& Scope, const AFGBuildableManufacturerVariablePower* Self)
            { const float D = Density(Self); if (D != 1.0f) Scope.Override(Scope(Self) * D); });
        MaxHook = SUBSCRIBE_METHOD(AFGBuildableManufacturerVariablePower::GetMaxPowerConsumption,
            [](auto& Scope, const AFGBuildableManufacturerVariablePower* Self)
            { const float D = Density(Self); if (D != 1.0f) Scope.Override(Scope(Self) * D); });
        const FIntProperty* PotentialSlots = FindFProperty<FIntProperty>(AFGBuildableFactory::StaticClass(), TEXT("mPotentialShardSlots"));
        check(PotentialSlots);
        FactoryHook = SUBSCRIBE_METHOD_VIRTUAL_AFTER(AFGBuildableFactory::BeginPlay,
            GetMutableDefault<AFGBuildableFactory>(),
            [PotentialSlots](AFGBuildableFactory* Self)
            {
                if (!Self->GetClass()->GetOutermost()->GetName().StartsWith(TEXT("/WorldBalance/"))) return;
                if (PotentialSlots->GetPropertyValue_InContainer(Self) != 0 || Self->CanChangeProductionBoost()) return;
                WorldBalance::InitializePotentialInventory(Self->GetPotentialInventory());
            });
        ExtractorHook = SUBSCRIBE_METHOD_VIRTUAL_AFTER(AFGBuildableResourceExtractor::BeginPlay,
            GetMutableDefault<AFGBuildableResourceExtractor>(),
            [](AFGBuildableResourceExtractor* Self)
            {
                if (!Self->GetClass()->GetOutermost()->GetName().StartsWith(TEXT("/WorldBalance/"))) return;
                TInlineComponentArray<UFGFactoryConnectionComponent*> Connections(Self);
                for (UFGFactoryConnectionComponent* Connection : Connections)
                {
                    if (Connection->GetDirection() != EFactoryConnectionDirection::FCD_OUTPUT) continue;
                    Connection->SetInventory(Self->GetOutputInventory());
                    Connection->SetInventoryAccessIndex(0);
                    Connection->SetForwardPeekAndGrabToBuildable(false);
                }
            });
#endif
    }
    virtual void ShutdownModule() override
    {
#if !WITH_EDITOR
        UNSUBSCRIBE_METHOD(AFGBuildableManufacturerVariablePower::GetProducingPowerConsumptionBase, PowerHook);
        UNSUBSCRIBE_METHOD(AFGBuildableManufacturerVariablePower::GetMinPowerConsumption, MinHook);
        UNSUBSCRIBE_METHOD(AFGBuildableManufacturerVariablePower::GetMaxPowerConsumption, MaxHook);
        UNSUBSCRIBE_METHOD(AFGBuildableFactory::BeginPlay, FactoryHook);
        UNSUBSCRIBE_METHOD(AFGBuildableResourceExtractor::BeginPlay, ExtractorHook);
#endif
    }
    virtual bool SupportsDynamicReloading() override { return false; }
private:
    FDelegateHandle PowerHook, MinHook, MaxHook, FactoryHook, ExtractorHook;
};

IMPLEMENT_MODULE(FWorldBalanceModule, WorldBalance)
