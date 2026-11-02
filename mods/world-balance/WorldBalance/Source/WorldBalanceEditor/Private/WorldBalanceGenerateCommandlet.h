#pragma once
#include "CoreMinimal.h"
#include "Commandlets/Commandlet.h"
#include "WorldBalanceGenerateCommandlet.generated.h"

UCLASS()
class UWorldBalanceGenerateCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    UWorldBalanceGenerateCommandlet();
    virtual int32 Main(const FString& Params) override;
};
