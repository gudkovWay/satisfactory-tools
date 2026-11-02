#pragma once

class UFGInventoryComponent;

namespace WorldBalance
{
    // Only for a potential inventory whose authored layout has no overclock or production-boost slots.
    void InitializePotentialInventory(UFGInventoryComponent* Inventory);
}
