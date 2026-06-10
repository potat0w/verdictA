"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import { cn, tokens } from "@/lib/theme";
import { clearToken, getToken } from "@/lib/api";
import { decodeJwt, getCurrentUser, isTokenExpired } from "@/lib/auth";

export default function ProfilePage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const t = getToken();
    if (!t) {
      router.replace("/login");
      return;
    }
    if (isTokenExpired(t)) {
      clearToken();
      router.replace("/login");
      return;
    }
    setToken(t);
  }, [router]);

  const user = useMemo(() => (token ? getCurrentUser() : null), [token]);

  if (!token || !user) {
    return null;
  }

  const payload = decodeJwt(token) || {};

  return (
    <div className={cn(tokens.bg.gradient, "min-h-screen py-12")}>
      <div className={cn(tokens.container)}>
        {/* Profile Header */}
        <div className="text-center mb-12">
          <h1 className={cn(tokens.heading, "text-5xl mb-4")}>Profile</h1>
          <p className="text-white/70 text-lg max-w-2xl mx-auto">
            Manage your account settings and view your profile information
          </p>
        </div>

        {/* Profile Avatar and Main Info */}
        <div className="mb-8">
          <Card className="p-8 text-center">
            <div className="flex flex-col items-center space-y-6">
              {/* Avatar Placeholder */}
              <div className={cn(tokens.iconBadge, "w-24 h-24 text-3xl")}>
                {user.username.charAt(0).toUpperCase()}
              </div>

              <div>
                <h2 className="text-3xl font-bold text-white mb-2">
                  {user.username}
                </h2>
                <p className="text-white/70">Account Member</p>
              </div>
            </div>
          </Card>
        </div>

        {/* Profile Details Grid */}
        <div className="grid lg:grid-cols-3 gap-6 mb-8">
          {/* Account Information */}
          <Card className="p-6">
            <div className="flex items-center mb-4">
              <div className={cn(tokens.iconBadge, "w-10 h-10 text-lg mr-3")}>
                <svg
                  className="w-5 h-5"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-white">
                Account Details
              </h3>
            </div>
            <div className="space-y-4">
              <div className="flex justify-between items-center py-2 border-b border-white/10">
                <span className="text-white/60">Username</span>
                <span className="text-white font-medium">{user.username}</span>
              </div>
              {user.expiresAtMs && (
                <div className="flex justify-between items-center py-2 border-b border-white/10">
                  <span className="text-white/60">Member Since</span>
                  <span className="text-white font-medium">
                    {new Date(user.expiresAtMs).toLocaleDateString()}
                  </span>
                </div>
              )}
              <div className="flex justify-between items-center py-2">
                <span className="text-white/60">Status</span>
                <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-sm">
                  Active
                </span>
              </div>
            </div>
          </Card>

          {/* Session Information */}
          <Card className="p-6">
            <div className="flex items-center mb-4">
              <div className={cn(tokens.iconBadge, "w-10 h-10 text-lg mr-3")}>
                <svg
                  className="w-5 h-5"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-white">Session Info</h3>
            </div>
            <div className="space-y-4">
              {user.expiresAtMs && (
                <div className="flex justify-between items-center py-2 border-b border-white/10">
                  <span className="text-white/60">Token Expires</span>
                  <span className="text-white font-medium">
                    {new Date(user.expiresAtMs).toLocaleString()}
                  </span>
                </div>
              )}
              <div className="flex justify-between items-center py-2">
                <span className="text-white/60">Last Login</span>
                <span className="text-white font-medium">
                  {new Date().toLocaleDateString()}
                </span>
              </div>
            </div>
          </Card>

          {/* Quick Actions */}
          <Card className="p-6">
            <div className="flex items-center mb-4">
              <div className={cn(tokens.iconBadge, "w-10 h-10 text-lg mr-3")}>
                <svg
                  className="w-5 h-5"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.286c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.286-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.286c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-white">
                Quick Actions
              </h3>
            </div>
            <div className="space-y-3">
              <Button
                variant="outline"
                className="w-full justify-center"
                onClick={() => router.push("/")}
              >
                Back to Home
              </Button>
              <Button
                variant="ghost"
                className="w-full justify-center"
                onClick={() => {
                  clearToken();
                  router.replace("/");
                }}
              >
                Sign Out
              </Button>
            </div>
          </Card>
        </div>

        {/* Technical Details */}
        <Card className="p-6">
          <div className="flex items-center mb-4">
            <div className={cn(tokens.iconBadge, "w-10 h-10 text-lg mr-3")}>
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-white">
              Technical Details
            </h3>
          </div>
          <div className="bg-black/30 rounded-lg p-4">
            <p className="text-white/60 text-sm mb-2">JWT Token Payload:</p>
            <pre className="text-sm text-white/80 overflow-auto max-h-64">
              {JSON.stringify(payload, null, 2)}
            </pre>
          </div>
        </Card>
      </div>
    </div>
  );
}
