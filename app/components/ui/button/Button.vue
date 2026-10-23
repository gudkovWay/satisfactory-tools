<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { Primitive, type PrimitiveProps } from 'reka-ui'
import { type ButtonVariants, buttonVariants } from '.'
import { cn } from '~/lib/utils/shadcn'

interface Props extends PrimitiveProps {
  variant?: ButtonVariants['variant']
  size?: ButtonVariants['size']
  class?: HTMLAttributes['class']
}
const props = withDefaults(defineProps<Props>(), { as: 'button' })
</script>

<template>
  <Primitive :as="as" :as-child="asChild" :class="cn(buttonVariants({ variant: props.variant, size: props.size }), props.class, 'rounded-md')">
    <slot />
  </Primitive>
</template>
