"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Button from "@/components/ui/Button";
import { cn, tokens } from "@/lib/theme";
import { registerUser } from "@/lib/api";

export default function SignupPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setIsLoading(true);
    try {
      await registerUser(username.trim(), password);
      setSuccess("Account created. Redirecting to login...");
      setTimeout(() => router.push("/login"), 1000);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Signup failed";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={cn(tokens.bg.gradient, "min-h-screen flex items-center justify-center p-4")}> 
      <div className="w-full max-w-md p-8 rounded-2xl bg-[rgba(15,28,36,0.9)] backdrop-blur-md border border-[#DCBC8C]/30 shadow-xl"> 
        <h1 className={cn(tokens.heading, "text-3xl mb-2 text-center")}>
          Create your account
        </h1>
        <p className="text-white/70 text-center mb-8">Sign up to start using VerdictAI</p>

        {error && <div className="mb-4 text-sm text-red-400">{error}</div>}
        {success && <div className="mb-4 text-sm text-green-400">{success}</div>}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block mb-2 font-semibold">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 rounded-lg bg-[#0e1a22]/80 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-[var(--primary-gold)]"
              placeholder="choose-a-username"
              required
            />
          </div>
          <div>
            <label className="block mb-2 font-semibold">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 rounded-lg bg-[#0e1a22]/80 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-[var(--primary-gold)]"
              placeholder="minimum 6 characters"
              required
            />
          </div>
          <div>
            <label className="block mb-2 font-semibold">Confirm Password</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-4 py-3 rounded-lg bg-[#0e1a22]/80 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-[var(--primary-gold)]"
              placeholder="re-enter password"
              required
            />
          </div>
          <Button 
            type="submit" 
            disabled={isLoading} 
            className="w-full bg-[var(--primary-gold)] text-[#0f1c24] hover:brightness-110 px-5 py-2.5 rounded-lg font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary-gold)] border-none"
          >
            {isLoading ? "Creating account..." : "Create account"}
          </Button>
        </form>

        <p className="text-center text-white/70 mt-6">
          Already have an account? {" "}
          <Link href="/login" className="text-[var(--primary-gold)] hover:underline">Log in</Link>
        </p>
      </div>
    </div>
  );
}