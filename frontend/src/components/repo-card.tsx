import type { Repo } from "@/lib/types";
import { cn } from "@/lib/utils";
import { GitFork, Star } from "lucide-react";
import Link from "next/link";

const LANGUAGE_COLORS: Record<string, string> = {
  TypeScript: "#3178c6",
  JavaScript: "#f1e05a",
  Python: "#3572a5",
  Rust: "#dea584",
  Go: "#00add8",
  Java: "#b07219",
  Ruby: "#701516",
  C: "#555555",
  "C++": "#f34b7d",
  Shell: "#89e051",
  HTML: "#e34c26",
  CSS: "#563d7c",
};

function formatCount(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

export function RepoCard({
  repo,
  className,
  linkToProject = true,
}: {
  repo: Repo;
  className?: string;
  linkToProject?: boolean;
}) {
  const inner = (
    <div
      className={cn(
        "rounded-lg border border-border-strong bg-surface-2 p-3 transition-colors",
        linkToProject && "hover:border-accent/60",
        className,
      )}
    >
      <div className="flex items-center gap-2">
        <span className="font-mono text-sm font-medium text-fg">
          {repo.owner_login}/<span className="text-accent">{repo.name}</span>
        </span>
      </div>
      {repo.description && (
        <p className="mt-1 line-clamp-2 text-sm text-muted">{repo.description}</p>
      )}
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
        {repo.language && (
          <span className="flex items-center gap-1.5">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: LANGUAGE_COLORS[repo.language] ?? "#8b97a6" }}
            />
            {repo.language}
          </span>
        )}
        <span className="flex items-center gap-1">
          <Star className="h-3.5 w-3.5" />
          {formatCount(repo.stargazers_count)}
        </span>
        <span className="flex items-center gap-1">
          <GitFork className="h-3.5 w-3.5" />
          {formatCount(repo.forks_count)}
        </span>
      </div>
    </div>
  );

  if (!linkToProject) return inner;

  return (
    <Link href={`/projects/${repo.owner_login}/${repo.name}`} className="block">
      {inner}
    </Link>
  );
}
