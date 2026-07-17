<template>
  <div 
    ref="container" 
    class="canvas-container"
    :style="{
      backgroundSize: `${32 * scale}px ${32 * scale}px`,
      backgroundPosition: `${pan.x}px ${pan.y}px`
    }"
    @mousedown="startPan"
    @mousemove="doPan"
    @mouseup="endPan"
    @mouseleave="endPan"
    @wheel="handleWheel"
  >
    <div 
      class="canvas-grid" 
      :style="{
        transform: `translate3d(${pan.x}px, ${pan.y}px, 0) scale(${scale})`
      }"
    >
      <!-- SVG Overlay for drawing connections -->
      <slot name="svg"></slot>
      
      <!-- Nodes slot -->
      <slot></slot>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const props = defineProps({
  scale: {
    type: Number,
    required: true
  },
  pan: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['update:scale', 'update:pan']);

const container = ref(null);
const isPanning = ref(false);
const startMouse = ref({ x: 0, y: 0 });
const startPanOffset = ref({ x: 0, y: 0 });

const startPan = (e) => {
  // Only pan on background click (class canvas-grid or container) or middle mouse click
  if (
    e.button === 1 || 
    e.target.classList.contains('canvas-container') || 
    e.target.classList.contains('canvas-grid')
  ) {
    isPanning.value = true;
    startMouse.value = { x: e.clientX, y: e.clientY };
    startPanOffset.value = { ...props.pan };
    e.preventDefault();
  }
};

const doPan = (e) => {
  if (!isPanning.value) return;
  const dx = e.clientX - startMouse.value.x;
  const dy = e.clientY - startMouse.value.y;
  emit('update:pan', {
    x: startPanOffset.value.x + dx,
    y: startPanOffset.value.y + dy
  });
};

const endPan = () => {
  isPanning.value = false;
};

const handleWheel = (e) => {
  e.preventDefault();
  const zoomFactor = 1.1;
  let newScale = props.scale;
  
  if (e.deltaY < 0) {
    newScale = Math.min(3.0, props.scale * zoomFactor);
  } else {
    newScale = Math.max(0.15, props.scale / zoomFactor);
  }
  
  if (newScale === props.scale) return;
  
  const rect = container.value.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;
  
  const dx = mouseX - props.pan.x;
  const dy = mouseY - props.pan.y;
  
  const newPan = {
    x: mouseX - dx * (newScale / props.scale),
    y: mouseY - dy * (newScale / props.scale)
  };
  
  emit('update:scale', newScale);
  emit('update:pan', newPan);
};
</script>
