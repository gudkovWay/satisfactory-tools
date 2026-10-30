import { type VariantProps, cva } from 'class-variance-authority'

export const selectTriggerVariants = cva('min-w-0', {
  variants: {
    variant: {
      default: '',
      filled: 'bg-elements-background',
      settings: 'bg-background min-h-12 px-4 py-3 text-base font-normal',
    },
    borderless: {
      true: 'border-transparent hover:border-transparent',
      false: '',
    },
    wrapLabels: {
      true: 'h-auto min-h-12 whitespace-normal [&>span]:break-words',
      false: '[&>span]:truncate',
    },
  },
  defaultVariants: { variant: 'settings', borderless: false, wrapLabels: true },
})

export type SelectTriggerVariants = VariantProps<typeof selectTriggerVariants>
