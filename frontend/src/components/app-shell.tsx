"use client";

import { cn } from "@/lib/utils";
import { useAuth } from "@/providers/auth-provider";
import { FolderGit2, Home, LogOut, Search, Settings, User } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Avatar } from "./ui/avatar";

function useNav() {
  const { profile } = useAuth();
  return [
    { href: "/", label: "Feed", icon: Home },
    { href: "/search", label: "Explore", icon: Search },
    { href: "/projects", label: "Projects", icon: FolderGit2 },
    {
      href: profile ? `/${profile.username}` : "/",
      label: "Profile",
      icon: User,
    },
    { href: "/settings", label: "Settings", icon: Settings },
  ];
}

function NavLink({
  href,
  label,
  icon: Icon,
  active,
}: {
  href: string;
  label: string;
  icon: typeof Home;
  active: boolean;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
        active
          ? "bg-surface-2 text-fg"
          : "text-muted hover:bg-surface-2 hover:text-fg",
      )}
    >
      <Icon className="h-5 w-5" />
      <span>{label}</span>
    </Link>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const nav = useNav();
  const { profile, logout } = useAuth();

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-6xl">
      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-border-strong px-3 py-5 md:flex">
        <Link href="/" className="mb-6 flex items-center gap-2 px-3">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-accent font-mono text-sm font-bold text-accent-fg">
            {"</>"}
          </span>
          <span className="text-lg font-semibold tracking-tight">ThreadSpace</span>
        </Link>

        <nav className="flex flex-1 flex-col gap-1">
          {nav.map((item) => (
            <NavLink key={item.label} {...item} active={isActive(item.href)} />
          ))}
        </nav>

        {profile && (
          <div className="mt-auto flex items-center gap-3 rounded-lg px-2 py-2 hover:bg-surface-2">
            <Avatar src={profile.profileimg} username={profile.username} size={36} />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{profile.username}</p>
              <p className="truncate text-xs text-faint">
                {profile.followers_count} followers
              </p>
            </div>
            <button
              onClick={logout}
              title="Log out"
              className="rounded-md p-1.5 text-faint transition-colors hover:bg-elevated hover:text-danger"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        )}
      </aside>

      {/* Mobile top bar */}
      <header className="glass fixed inset-x-0 top-0 z-20 flex items-center justify-between border-b border-border-strong px-4 py-3 md:hidden">
        <Link href="/" className="flex items-center gap-2">
          <span className="grid h-7 w-7 place-items-center rounded-md bg-accent font-mono text-xs font-bold text-accent-fg">
            {"</>"}
          </span>
          <span className="font-semibold">ThreadSpace</span>
        </Link>
        {profile && (
          <button onClick={logout} className="text-faint hover:text-danger">
            <LogOut className="h-5 w-5" />
          </button>
        )}
      </header>

      <main className="min-h-screen flex-1 px-4 pb-24 pt-20 md:px-8 md:py-8">
        <div className="mx-auto w-full max-w-2xl">{children}</div>
      </main>

      {/* Mobile bottom nav */}
      <nav className="glass fixed inset-x-0 bottom-0 z-20 flex items-center justify-around border-t border-border-strong py-2 md:hidden">
        {nav.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.label}
              href={item.href}
              className={cn(
                "flex flex-col items-center gap-0.5 px-4 py-1 text-xs",
                isActive(item.href) ? "text-accent" : "text-faint",
              )}
            >
              <Icon className="h-5 w-5" />
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
