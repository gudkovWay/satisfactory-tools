import { type VariantProps, cva } from 'class-variance-authority'

export { default as Button } from './Button.vue'

export const buttonVariants = cva(
  'atlas-button inline-flex w-auto min-w-0 items-center justify-center gap-2 whitespace-normal text-center text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50',
  {
    variants: {
      variant: {
        primary: 'atlas-button-primary bg-primary-background text-primary-foreground',
        ghost: 'text-foreground hover:bg-elements-background bg-transparent',
        outline: 'border-based-border text-foreground hover:bg-elements-background border bg-transparent',
      },
      size: {
        large: 'min-h-12 px-4 py-2.5',
        medium: 'min-h-11 px-3.5 py-2.5',
      },
    },
    defaultVariants: { variant: 'primary', size: 'medium' },
  },
)

export type ButtonVariants = VariantProps<typeof buttonVariants>
