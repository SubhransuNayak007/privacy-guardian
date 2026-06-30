"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { motion } from "framer-motion";
import { flushSync } from "react-dom";

export function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <div className="w-16 h-8 rounded-full bg-surface-elevated/50" />;
  }

  const isDark = resolvedTheme === "dark";

  const toggleTheme = (e: React.MouseEvent) => {
    const nextTheme = isDark ? "light" : "dark";

    // View Transitions API for warp effect
    if (!document.startViewTransition) {
      setTheme(nextTheme);
      return;
    }

    // Get the click position for the warp origin
    const x = e.clientX;
    const y = e.clientY;
    const endRadius = Math.hypot(
      Math.max(x, window.innerWidth - x),
      Math.max(y, window.innerHeight - y)
    );

    const transition = document.startViewTransition(() => {
      flushSync(() => {
        setTheme(nextTheme);
      });
    });

    transition.ready.then(() => {
      const clipPath = [
        `circle(0px at ${x}px ${y}px)`,
        `circle(${endRadius}px at ${x}px ${y}px)`,
      ];

      document.documentElement.animate(
        {
          clipPath: clipPath,
        },
        {
          duration: 400,
          easing: "cubic-bezier(0.4, 0, 0.2, 1)",
          pseudoElement: "::view-transition-new(root)",
        }
      );
    });
  };

  return (
    <button
      onClick={toggleTheme}
      className="relative flex items-center min-w-[64px] min-h-[44px] p-1 rounded-full transition-colors duration-300 bg-surface-glass border border-border shadow-soft hover:shadow-card focus:outline-none focus:ring-2 focus:ring-primary overflow-hidden"
      aria-label="Toggle Theme"
    >
      <motion.div
        initial={false}
        animate={{
          left: isDark ? "calc(100% - 36px)" : "4px",
        }}
        transition={{
          type: "spring",
          stiffness: 400,
          damping: 30,
        }}
        className={`absolute flex items-center justify-center w-8 h-8 rounded-full shadow-sm ${
          isDark ? "bg-accent-dark text-background" : "bg-surface-elevated text-primary"
        }`}
      >
        {isDark ? <Moon size={12} strokeWidth={3} /> : <Sun size={12} strokeWidth={3} />}
      </motion.div>
      <div className="flex w-full justify-between px-2 text-secondary-text opacity-50 z-[-1]">
        <Sun size={14} />
        <Moon size={14} />
      </div>
    </button>
  );
}
