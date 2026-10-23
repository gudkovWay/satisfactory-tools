import { type VariantProps, cva } from 'class-variance-authority'

export const selectTriggerVariants = cva('min-w-0', {
  variants: {
    variant: {
      default: '',
      filled: 'bg-elements-background',
      settings: 'bg-elements-background min-h-11 px-3 py-2 text-base font-normal',
    },
    borderless: {
      true: 'border-transparent hover:border-transparent',
      false: '',
    },
    wrapLabels: {
      true: 'h-auto min-h-11 whitespace-normal [&>span]:break-words',
      false: '[&>span]:truncate',
    },
  },
  defaultVariants: { variant: 'settings', borderless: false, wrapLabels: true },
})

export type SelectTriggerVariants = VariantProps<typeof selectTriggerVariants>
