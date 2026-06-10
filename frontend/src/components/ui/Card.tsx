import { HTMLAttributes } from "react";
import { cn, tokens } from "@/lib/theme";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  interactive?: boolean;
}

export default function Card({ className, interactive, ...props }: CardProps) {
  return (
    <div
      className={cn(
        tokens.surface.card,
        "border-none",
        interactive && "hover:shadow-xl hover:shadow-[rgba(200,171,127,0.15)] transition-shadow",
        className
      )}
      {...props}
    />
  );
}