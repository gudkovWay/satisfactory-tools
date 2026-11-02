#include "WorldBalanceCatalog.h"

namespace WorldBalance
{
    FString AssetPath(const TCHAR* Prefix, const FString& Id)
    {
        const FString Name = FString(Prefix) + TEXT("_WB_") + Id;
        return TEXT("/WorldBalance/Generated/") + Name + TEXT(".") + Name + TEXT("_C");
    }

    FString VanillaRecipePath(const FString& Name)
    {
        return TEXT("/Game/FactoryGame/Recipes/Buildings/Recipe_") + Name + TEXT(".Recipe_") + Name + TEXT("_C");
    }

    TConstArrayView<FMilestone> Milestones()
    {
        static const FMilestone Values[] = {
            {TEXT("Mining1"), TEXT("World Balance: Extraction I"), 1, 100},
            {TEXT("Mining2"), TEXT("World Balance: Extraction II"), 3, 200},
            {TEXT("Mining3"), TEXT("World Balance: Extraction III"), 5, 400},
            {TEXT("Mining4"), TEXT("World Balance: Extraction IV"), 8, 800},
            {TEXT("Density10"), TEXT("World Balance: Production x10"), 3, 200},
            {TEXT("Density15"), TEXT("World Balance: Production x15"), 5, 400},
            {TEXT("EarlyCoal"), TEXT("World Balance: Autonomous Power"), 2, 150},
            {TEXT("Water4"), TEXT("World Balance: High Capacity Water and Coal"), 6, 400},
            {TEXT("Oil2"), TEXT("World Balance: Oil Extraction II"), 8, 800},
            {TEXT("Fuel10"), TEXT("World Balance: Fuel Power II"), 7, 600},
            {TEXT("Fuel15"), TEXT("World Balance: Fuel Power III"), 8, 800}
        };
        return MakeArrayView(Values);
    }

    const TArray<FBuilding>& Buildings()
    {
        static const TArray<FBuilding> Values = []
        {
            TArray<FBuilding> Rows;
            auto Add = [&Rows](const FString& Id, const FString& Folder, const FString& Name,
                const FString& Recipe, const FString& Gate, EKind Kind, float Scale,
                float Power = 0, int32 Outputs = 1, bool RequireVanilla = true)
            {
                Rows.Add({Id, TEXT("/Game/FactoryGame/Buildable/Factory/") + Folder +
                    TEXT("/Build_") + Name + TEXT(".Build_") + Name + TEXT("_C"),
                    Recipe, Gate, Kind, Scale, Power, Outputs, RequireVanilla});
            };
            const TCHAR* Manufacturers[] = {TEXT("SmelterMk1"), TEXT("FoundryMk1"), TEXT("ConstructorMk1"),
                TEXT("AssemblerMk1"), TEXT("ManufacturerMk1"), TEXT("OilRefinery"), TEXT("Packager"),
                TEXT("Blender"), TEXT("HadronCollider"), TEXT("Converter"), TEXT("QuantumEncoder")};
            for (const TCHAR* Name : Manufacturers)
            {
                for (int32 D : {5, 10, 15})
                {
                    const FString Gate = D == 5 ? TEXT("") : FString::Printf(TEXT("Density%d"), D);
                    const FString Recipe = FString(Name) == TEXT("FoundryMk1") ? TEXT("SmelterMk1") :
                        FString(Name) == TEXT("SmelterMk1") ? TEXT("SmelterBasicMk1") : FString(Name);
                    Add(FString::Printf(TEXT("%s_D%d"), Name, D), Name, Name, Recipe, Gate, EKind::Production, D);
                }
            }
            const int32 Outputs[] = {2, 3, 4, 6};
            const int32 Speeds[] = {750, 1000, 1500, 1800};
            for (int32 Index = 0; Index < 4; ++Index)
            {
                const FString Gate = FString::Printf(TEXT("Mining%d"), Index + 1);
                const FString Parent = FString::Printf(TEXT("MinerMk%d"), FMath::Min(Index + 1, 3));
                Add(FString::Printf(TEXT("Miner%d"), Index + 1), Index == 0 ? TEXT("MinerMK1") : Parent,
                    Parent, Parent, Gate, EKind::Miner, 240 * (1 << Index), 20 * (1 << Index), Outputs[Index], false);
                for (bool Lift : {false, true})
                {
                    const FString Name = FString::Printf(TEXT("Conveyor%sMk%d"), Lift ? TEXT("Lift") : TEXT("Belt"), Index + 1);
                    Add(FString::Printf(TEXT("%s%d"), Lift ? TEXT("Lift") : TEXT("Belt"), Index + 1),
                        Name, Name, Name, Gate, Lift ? EKind::Lift : EKind::Belt, Speeds[Index], 0, 1, false);
                }
            }
            Add(TEXT("Oil1"), TEXT("OilPump"), TEXT("OilPump"), TEXT("OilPump"), TEXT(""), EKind::Oil, 2, 80, 6);
            Add(TEXT("Oil2"), TEXT("OilPump"), TEXT("OilPump"), TEXT("OilPump"), TEXT("Oil2"), EKind::Oil, 4, 160, 6);
            Add(TEXT("Water2"), TEXT("WaterPump"), TEXT("WaterPump"), TEXT("WaterPump"), TEXT("EarlyCoal"), EKind::Water, 2, 40, 1, false);
            Add(TEXT("Water4"), TEXT("WaterPump"), TEXT("WaterPump"), TEXT("WaterPump"), TEXT("Water4"), EKind::Water, 4, 80);
            Add(TEXT("Biomass5"), TEXT("GeneratorBiomass"), TEXT("GeneratorBiomass_Automated"), TEXT("GeneratorBiomass_Automated"), TEXT(""), EKind::Generator, 5);
            Add(TEXT("Coal5"), TEXT("GeneratorCoal"), TEXT("GeneratorCoal"), TEXT("GeneratorCoal"), TEXT("EarlyCoal"), EKind::Generator, 5, 0, 1, false);
            Add(TEXT("Coal10"), TEXT("GeneratorCoal"), TEXT("GeneratorCoal"), TEXT("GeneratorCoal"), TEXT("Water4"), EKind::Generator, 10);
            for (int32 D : {5, 10, 15})
            {
                Add(FString::Printf(TEXT("Fuel%d"), D), TEXT("GeneratorFuel"), TEXT("GeneratorFuel"), TEXT("GeneratorFuel"),
                    D == 5 ? TEXT("") : FString::Printf(TEXT("Fuel%d"), D), EKind::Generator, D);
                Add(FString::Printf(TEXT("Storage%d"), D), TEXT("PowerStorage"), TEXT("PowerStorageMk1"), TEXT("PowerStorageMk1"),
                    D == 5 ? TEXT("") : FString::Printf(TEXT("Density%d"), D), EKind::Storage, D);
            }
            Add(TEXT("Nuclear2"), TEXT("GeneratorNuclear"), TEXT("GeneratorNuclear"), TEXT("GeneratorNuclear"), TEXT(""), EKind::Generator, 2);
            return Rows;
        }();
        return Values;
    }
}
