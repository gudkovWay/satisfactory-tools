<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import Select from './ui/select/Select.vue'
import SelectTrigger from './ui/select/SelectTrigger.vue'
import SelectContent from './ui/select/SelectContent.vue'
import SelectItem from './ui/select/SelectItem.vue'
import SelectValue from './ui/select/SelectValue.vue'
import { type SelectTriggerVariants, selectTriggerVariants } from './ui/select/selectVariants'

interface Option {
  label: string
  value: string | number
  disabled?: boolean
}

defineOptions({ inheritAttrs: false })
const props = withDefaults(defineProps<{
  modelValue: string | number | null | undefined
  options: readonly Option[]
  triggerId?: string
  placeholder?: string
  variant?: NonNullable<SelectTriggerVariants['variant']>
  wrapLabels?: boolean
  borderless?: boolean
  disabled?: boolean
  disabledTrigger?: boolean
  isLoading?: boolean
  error?: boolean
  describedBy?: string
  class?: HTMLAttributes['class']
}>(), { variant: 'settings', wrapLabels: true, placeholder: 'Выбери значение' })
const emit = defineEmits<{ (e: 'update:modelValue', value: string | number): void }>()
const generatedId = useId()
const selectedLabel = computed(() => props.options.find(option => option.value === props.modelValue)?.label)

function updateValue(value: unknown) {
  if (typeof value === 'string' || typeof value === 'number') emit('update:modelValue', value)
}
</script>

<template>
  <div data-slot="the-select" class="w-full min-w-0" :class="props.class">
    <Select :model-value="props.modelValue ?? undefined" :disabled="props.disabled || props.disabledTrigger" @update:model-value="updateValue">
      <SelectTrigger
        v-bind="$attrs"
        :id="props.triggerId || generatedId"
        :aria-invalid="props.error || undefined"
        :aria-describedby="props.describedBy"
        :aria-busy="props.isLoading || undefined"
        :class="[
          selectTriggerVariants({ variant: props.variant, wrapLabels: props.wrapLabels, borderless: props.borderless }),
          props.error && 'border-destructive hover:border-destructive focus-visible:border-destructive',
        ]"
      >
        <SelectValue :placeholder="props.placeholder" class="min-w-0 flex-1 text-left">{{ selectedLabel || props.placeholder }}</SelectValue>
      </SelectTrigger>
      <SelectContent>
        <p v-if="props.isLoading" role="status" class="px-3 py-3 text-sm font-normal text-muted-foreground">Загружаем варианты.</p>
        <template v-else>
          <SelectItem v-for="option in props.options" :key="option.value" :value="option.value" :disabled="option.disabled">{{ option.label }}</SelectItem>
          <p v-if="!props.options.length" role="status" class="px-3 py-3 text-sm font-normal text-muted-foreground">Здесь нет данных.</p>
        </template>
      </SelectContent>
    </Select>
  </div>
</template>
