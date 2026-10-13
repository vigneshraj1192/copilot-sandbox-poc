from sandbox.repo_map_engine import ProductionRepoMapEngine
from sandbox.repo_sandbox import RepoSandbox

# 1. Target a public repository
TARGET_REPO = "https://github.com/jonahandersson/dotnet-minimal-web-api-example.git"

# 2. Instantiate sandbox
sandbox = RepoSandbox(repo_url=TARGET_REPO)

try:
    # 3. Clone
    sandbox.clone()

    # 4. Run build/compile verification inside an isolated official Python container
    # Here, we test compiling all Python files to bytecode as a basic syntax/build check
    exit_code = sandbox.run_in_docker(
        image="mcr.microsoft.com/dotnet/sdk:8.0",
        command="dotnet build DotNetMinimalAPIDemo/DotNetMinimalAPIDemo.csproj"
    )

    if exit_code == 0:
        print("\n Build / Compilation Check Passed!")
    else:
        print("\n Build Failed.")

    print("\n--- Generating Production Graph-Ranked Repo-Map ---")
    engine = ProductionRepoMapEngine(root_dir=sandbox.workspace_path, max_tokens=1024)
    repo_map = engine.generate_map()

    token_count = engine.count_tokens(repo_map)
    print(f"Total Output Tokens: {token_count} / {engine.max_tokens}\n")
    print(repo_map)

finally:
    # 5. Always clean up temporary files on the host
    sandbox.cleanup()