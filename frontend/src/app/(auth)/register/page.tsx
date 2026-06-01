"use client";

import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { errorMessage } from "@/lib/api";
import { useAuth } from "@/providers/auth-provider";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    password2: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const update = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (form.password !== form.password2) {
      setError("Passwords do not match");
      return;
    }
    setLoading(true);
    try {
      await register(form);
      router.replace("/");
    } catch (err) {
      setError(errorMessage(err, "Could not create account"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-2xl border border-border-strong bg-surface p-8 shadow-2xl shadow-black/40">
      <div className="mb-6 flex flex-col items-center text-center">
        <span className="mb-3 grid h-11 w-11 place-items-center rounded-xl bg-accent font-mono text-base font-bold text-accent-fg">
          {"</>"}
        </span>
        <h1 className="text-xl font-semibold">Join ThreadSpace</h1>
        <p className="text-sm text-muted">Share what you build in public</p>
      </div>

      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <Label htmlFor="username">Username</Label>
          <Input id="username" value={form.username} onChange={update("username")} required />
        </div>
        <div>
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            value={form.email}
            onChange={update("email")}
            required
          />
        </div>
        <div>
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            value={form.password}
            onChange={update("password")}
            autoComplete="new-password"
            required
          />
        </div>
        <div>
          <Label htmlFor="password2">Confirm password</Label>
          <Input
            id="password2"
            type="password"
            value={form.password2}
            onChange={update("password2")}
            autoComplete="new-password"
            required
          />
        </div>

        {error && (
          <p className="rounded-lg bg-danger/10 px-3 py-2 text-sm text-danger">
            {error}
          </p>
        )}

        <Button type="submit" loading={loading} className="w-full justify-center">
          Create account
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-muted">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-accent hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
