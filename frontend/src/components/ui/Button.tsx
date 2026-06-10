"use client";

import { ButtonHTMLAttributes } from "react";
import { cn, tokens } from "@/lib/theme";

export type ButtonVariant = "primary" | "outline" | "ghost";
export type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

export default function Button({
  className,
  variant = "primary",
  size = "md",
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        tokens.button.base,
        tokens.button[variant],
        tokens.button.size[size],
        "border-none",
        className
      )}
      {...props}
    />
  );
} 