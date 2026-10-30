import { type VariantProps, cva } from 'class-variance-authority'

export { default as Button } from './Button.vue'

export const buttonVariants = cva(
  'inline-flex w-auto min-w-0 items-center justify-center gap-2 whitespace-normal text-center text-base font-medium transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none',
  {
    variants: {
      variant: {
        primary: 'bg-primary-background text-primary-foreground hover:brightness-95 active:brightness-90',
        ghost: 'text-foreground hover:bg-surface bg-transparent active:bg-elements-background',
        outline: 'border-based-border text-foreground hover:bg-elements-background border bg-transparent active:opacity-80',
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
