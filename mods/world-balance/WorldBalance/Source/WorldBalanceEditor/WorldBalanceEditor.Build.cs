using UnrealBuildTool;

public class WorldBalanceEditor : ModuleRules
{
    public WorldBalanceEditor(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        CppStandard = CppStandardVersion.Cpp20;
        bUseUnity = false;
        PrivateDependencyModuleNames.AddRange(new[] {
            "Core", "CoreUObject", "Engine", "FactoryGame", "SML", "WorldBalance",
            "UnrealEd", "Kismet", "KismetCompiler", "BlueprintGraph", "AssetRegistry", "Projects"
        });
    }
}
