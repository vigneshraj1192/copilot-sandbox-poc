import collections
from pathlib import Path
from typing import Dict, List, Set, Tuple
import networkx as nx
import pathspec
import tiktoken

from .ast_tagger import ASTTagger
from .tag_cache import TagCache

class ProductionRepoMapEngine:
    DEFAULT_IGNORES = [
        ".git", ".git/**", "bin", "bin/**", "obj", "obj/**",
        "node_modules", "node_modules/**", "*.dll", "*.exe", "*.pdb",
        ".venv", ".venv/**", "__pycache__", "__pycache__/**"
    ]

    def __init__(self, root_dir: Path, max_tokens: int = 2048):
        self.root_dir = Path(root_dir).resolve()
        self.max_tokens = max_tokens
        self.tagger = ASTTagger()
        self.cache = TagCache(self.root_dir / ".repo_map_cache.db")
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.ignore_spec = self._build_ignore_spec()

    def _build_ignore_spec(self) -> pathspec.PathSpec:
        patterns = list(self.DEFAULT_IGNORES)
        gi = self.root_dir / ".gitignore"
        if gi.is_file():
            patterns.extend(gi.read_text(encoding="utf-8", errors="ignore").splitlines())
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)

    def _is_ignored(self, path: Path) -> bool:
        rel_path = path.relative_to(self.root_dir).as_posix()
        return self.ignore_spec.match_file(rel_path)

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text, disallowed_special=()))

    def scan_files(self) -> Dict[str, List[Dict]]:
        file_to_tags = {}
        for path in sorted(self.root_dir.rglob("*")):
            if not path.is_file() or self._is_ignored(path):
                continue

            rel_path = path.relative_to(self.root_dir).as_posix()
            try:
                data = path.read_bytes()
            except Exception:
                continue

            f_hash = TagCache.compute_hash(data)
            cached_tags = self.cache.get_tags(rel_path, f_hash)

            if cached_tags is not None:
                file_to_tags[rel_path] = cached_tags
            else:
                tags = self.tagger.extract_tags(path, data)
                self.cache.store_tags(rel_path, f_hash, tags)
                file_to_tags[rel_path] = tags

        return file_to_tags

    def rank_files(self, file_to_tags: Dict[str, List[Dict]]) -> List[Tuple[str, float]]:
        """Builds directed reference graph and computes PageRank."""
        G = nx.MultiDiGraph()

        # Map defined symbols -> files defining them
        def_map = collections.defaultdict(set)
        for rel_path, tags in file_to_tags.items():
            G.add_node(rel_path)
            for t in tags:
                if t["role"] == "def":
                    def_map[t["name"]].add(rel_path)

        # Connect caller file -> defining file
        for rel_path, tags in file_to_tags.items():
            for t in tags:
                if t["role"] == "ref" and t["name"] in def_map:
                    for target_file in def_map[t["name"]]:
                        if target_file != rel_path:
                            G.add_edge(rel_path, target_file)

        if len(G) == 0:
            return []

        try:
            scores = nx.pagerank(G, alpha=0.85, max_iter=100)
        except Exception:
            scores = {n: 1.0 / len(G) for n in G.nodes()}

        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    def generate_map(self) -> str:
        file_to_tags = self.scan_files()
        ranked = self.rank_files(file_to_tags)

        packed_blocks = []
        current_tokens = 0

        # Pack top-ranked files and their definitions first
        for rel_path, score in ranked:
            tags = file_to_tags.get(rel_path, [])
            defs = [t for t in tags if t["role"] == "def"]

            if not defs:
                continue

            block_lines = [f"{rel_path}:"]
            for d in defs:
                block_lines.append(f"  [{d['kind']}] {d['name']} (line {d['line']})")

            block_str = "\n".join(block_lines)
            block_tokens = self.count_tokens(block_str)

            if current_tokens + block_tokens <= (self.max_tokens - 100):
                packed_blocks.append(block_str)
                current_tokens += block_tokens
            else:
                break

        return "\n\n".join(packed_blocks)