<script setup lang="ts">
const props = withDefaults(defineProps<{
  name: string
  size?: number
}>(), {
  size: 18,
})

const paths: Record<string, string[]> = {
  dashboard: ['M3 13h8V3H3v10zm10 8h8V11h-8v10zM3 21h8v-6H3v6zm10-10h8V3h-8v8z'],
  checkin: ['M9 11l3 3L22 4', 'M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11'],
  jobs: ['M8 6h13', 'M8 12h13', 'M8 18h13', 'M3 6h.01', 'M3 12h.01', 'M3 18h.01'],
  sites: ['M3 6l9-4 9 4v12l-9 4-9-4V6z', 'M3 6l9 4 9-4', 'M12 10v12'],
  accounts: ['M20 21a8 8 0 0 0-16 0', 'M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z'],
  reports: ['M4 19V9', 'M10 19V5', 'M16 19v-7', 'M22 19v-3'],
  incidents: ['M12 9v4', 'M12 17h.01', 'M10.29 3.86 1.82 3.3a2 2 0 0 0 1.75 2.98h16.28a2 2 0 0 0 1.75-2.98l-8.14-14.7a2 2 0 0 0-3.5 0z'],
  schedules: ['M8 2v4', 'M16 2v4', 'M3 10h18', 'M5 6h14a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z'],
  settings: ['M12 3v2', 'M12 19v2', 'M4.93 4.93l1.41 1.41', 'M17.66 17.66l1.41 1.41', 'M3 12h2', 'M19 12h2', 'M4.93 19.07l1.41-1.41', 'M17.66 6.34l1.41-1.41', 'M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8z'],
  locale: ['M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2z', 'M2 12h20', 'M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z'],
  light: ['M12 3v2', 'M12 19v2', 'M5.64 5.64l1.41 1.41', 'M16.95 16.95l1.41 1.41', 'M3 12h2', 'M19 12h2', 'M5.64 18.36l1.41-1.41', 'M16.95 7.05l1.41-1.41', 'M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8z'],
  dark: ['M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z'],
  auto: ['M9 17H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v2', 'M12 19h6', 'M15 16l3 3 3-3'],
  logout: ['M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4', 'M16 17l5-5-5-5', 'M21 12H9'],
  eye: ['M2.06 12C3.6 7.94 7.44 5 12 5s8.4 2.94 9.94 7c-1.54 4.06-5.38 7-9.94 7S3.6 16.06 2.06 12z', 'M12 15.5A3.5 3.5 0 1 0 12 8.5a3.5 3.5 0 0 0 0 7z'],
  'eye-off': ['M3 3l18 18', 'M10.58 10.58A2 2 0 0 0 13.42 13.42', 'M9.88 5.09A10.94 10.94 0 0 1 12 5c4.56 0 8.4 2.94 9.94 7a11.8 11.8 0 0 1-4.16 5.15', 'M6.71 6.7C4.68 7.96 3.09 9.79 2.06 12c1.54 4.06 5.38 7 9.94 7 1.74 0 3.38-.43 4.82-1.2'],
}
</script>

<template>
  <svg
    class="app-icon"
    :width="props.size"
    :height="props.size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-linecap="round"
    stroke-linejoin="round"
    stroke-width="1.8"
    aria-hidden="true"
  >
    <path v-for="item in paths[props.name] || paths.dashboard" :key="item" :d="item" />
  </svg>
</template>
