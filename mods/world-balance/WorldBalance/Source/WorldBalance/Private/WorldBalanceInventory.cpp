#include "WorldBalanceInventory.h"
#include "FGInventoryComponent.h"

void WorldBalance::InitializePotentialInventory(UFGInventoryComponent* Inventory)
{
    if (!Inventory || Inventory->GetSizeLinear() > 1) return;

    // Vanilla interaction widgets read this inventory even when the building has no shard slots.
    if (Inventory->GetSizeLinear() == 0) Inventory->Resize(1);
    Inventory->SetLocked(true);
}
