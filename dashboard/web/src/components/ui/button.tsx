import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import type { ButtonHTMLAttributes } from "react"

import { cn } from "@/lib/cn"

const buttonVariants = cva("button", {
  variants: {
    variant: {
      default: "button-primary",
      ghost: "button-ghost",
      outline: "button-outline",
    },
    size: {
      default: "button-default",
      icon: "button-icon",
      compact: "button-compact",
    },
  },
  defaultVariants: {
    variant: "default",
    size: "default",
  },
})

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & { asChild?: boolean }

export function Button({ className, variant, size, asChild, ...props }: ButtonProps) {
  const Component = asChild ? Slot : "button"
  return (
    <Component
      className={cn(buttonVariants({ variant, size }), className)}
      data-ui="button"
      {...props}
    />
  )
}
