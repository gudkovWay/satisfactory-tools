using UnrealBuildTool;

public class WorldBalance : ModuleRules
{
    public WorldBalance(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        CppStandard = CppStandardVersion.Cpp20;
        bUseUnity = false;
        PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine", "FactoryGame", "SML" });
        PrivateDependencyModuleNames.AddRange(new[] { "AssetRegistry", "Projects" });
    }
}
