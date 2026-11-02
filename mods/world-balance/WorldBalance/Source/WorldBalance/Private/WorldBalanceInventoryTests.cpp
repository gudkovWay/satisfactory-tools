#include "Misc/AutomationTest.h"
#include "WorldBalanceInventory.h"
#include "Engine/World.h"
#include "FGInventoryComponent.h"
#include "GameFramework/Actor.h"
#include "Resources/FGItemDescriptor.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWorldBalancePotentialInventoryTest, "WorldBalance.Inventory.EmptyPotential",
    EAutomationTestFlags::ClientContext | EAutomationTestFlags::ServerContext | EAutomationTestFlags::EngineFilter)

bool FWorldBalancePotentialInventoryTest::RunTest(const FString&)
{
    UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
    if (!TestNotNull(TEXT("inventory test world"), World)) return false;
    World->InitializeNewWorld(UWorld::InitializationValues().CreatePhysicsScene(false).CreateNavigation(false)
        .CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false));
    AActor* Owner = World->SpawnActor<AActor>();
    if (TestNotNull(TEXT("inventory owner"), Owner))
    {
        auto* Empty = NewObject<UFGInventoryComponent>(Owner);
        Empty->Resize(0);
        WorldBalance::InitializePotentialInventory(Empty);
        if (TestEqual(TEXT("zero-slot potential inventory becomes readable"), Empty->GetSizeLinear(), 1))
            TestEqual(TEXT("opening the overclock widget reads zero shards"),
                Empty->GetNumItems(UFGItemDescriptor::StaticClass()), 0);
        TestTrue(TEXT("padding cannot accept items"), Empty->IsLocked());
        TestFalse(TEXT("padding rejects item insertion"), Empty->IsItemAllowed(UFGItemDescriptor::StaticClass(), 0));
        Empty->SetLocked(false);
        WorldBalance::InitializePotentialInventory(Empty);
        TestEqual(TEXT("repeated initialization keeps one padding slot"), Empty->GetSizeLinear(), 1);
        TestTrue(TEXT("replicated padding is locked even if it already exists"), Empty->IsLocked());

        auto* Existing = NewObject<UFGInventoryComponent>(Owner);
        Existing->Resize(3);
        Existing->SetLocked(false);
        WorldBalance::InitializePotentialInventory(Existing);
        TestEqual(TEXT("valid shard inventory is not resized"), Existing->GetSizeLinear(), 3);
        TestFalse(TEXT("valid shard inventory is not locked"), Existing->IsLocked());
    }
    World->DestroyWorld(false);
    return !HasAnyErrors();
}
#endif
