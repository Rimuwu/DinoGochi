<template>
  <div v-if="visible" class="item-modal-overlay" @click.self="$emit('close')">
    <div class="item-modal-dialog">
      
      <!-- Modal Header -->
      <div class="item-modal-header">
        <h3>🎒 Выберите предмет</h3>
        <button class="secondary close-btn" @click="$emit('close')">✕</button>
      </div>
      
      <!-- Search and Filters -->
      <div class="item-modal-filters">
        <input 
          v-model="searchQuery" 
          type="text" 
          placeholder="Поиск по названию или ID..." 
          class="search-input"
        />
        
        <div class="filter-chips">
          <!-- Rank Filters -->
          <button 
            v-for="rank in ranks" 
            :key="rank"
            class="filter-chip"
            :class="{ active: selectedRank === rank }"
            @click="selectedRank = selectedRank === rank ? '' : rank"
          >
            {{ translateRank(rank) }}
          </button>
        </div>

        <div class="filter-chips">
          <!-- File Category Filters -->
          <button 
            v-for="file in fileCategories" 
            :key="file"
            class="filter-chip category-chip"
            :class="{ active: selectedFile === file }"
            @click="selectedFile = selectedFile === file ? '' : file"
          >
            {{ file.replace('.json', '') }}
          </button>
        </div>
      </div>
      
      <!-- Items Grid -->
      <div class="item-modal-grid">
        <div 
          v-for="item in filteredItems" 
          :key="item.id"
          class="item-grid-card"
          :class="`rarity-${item.rank}`"
          @click="selectItem(item.id)"
        >
          <span class="item-grid-emoji">{{ item.emoji || '📦' }}</span>
          <span class="item-grid-name" :title="item.name">{{ item.name }}</span>
          <span class="item-grid-id">{{ item.id }}</span>
          <span class="item-grid-badge">{{ item.rank }}</span>
        </div>
        <div v-if="filteredItems.length === 0" class="no-items-message">
          Предметы не найдены
        </div>
      </div>
      
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  visible: {
    type: Boolean,
    required: true
  },
  allItems: {
    type: Object,
    required: true
  },
  localization: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['select', 'close']);

const searchQuery = ref('');
const selectedRank = ref('');
const selectedFile = ref('');

const ranks = ['common', 'uncommon', 'rare', 'epic', 'mystical', 'legendary', 'mythical'];

const fileCategories = computed(() => {
  return Object.keys(props.allItems).sort();
});

const selectItem = (itemId) => {
  emit('select', itemId);
};

// Local translation helpers
const t = (path) => {
  if (!props.localization || !props.localization.ru) return path;
  const parts = path.split('.');
  let current = props.localization.ru;
  for (const part of parts) {
    if (current[part] === undefined) return path;
    current = current[part];
  }
  return typeof current === 'string' ? current : path;
};

const getItemName = (itemId) => {
  const path = `items_names.${itemId}.name`;
  const name = t(path);
  if (name !== path) return name;
  return itemId;
};

const translateRank = (rank) => {
  const map = {
    common: 'Обычный',
    uncommon: 'Необычный',
    rare: 'Редкий',
    epic: 'Эпический',
    mystical: 'Мистический',
    legendary: 'Легендарный',
    mythical: 'Мифический'
  };
  return map[rank] || rank;
};

// Filtered list computed
const filteredItems = computed(() => {
  const q = searchQuery.value.toLowerCase();
  const list = [];
  
  for (const file in props.allItems) {
    // Apply file filter
    if (selectedFile.value && selectedFile.value !== file) continue;
    
    for (const id in props.allItems[file]) {
      const item = props.allItems[file][id];
      
      // Apply rank filter
      if (selectedRank.value && item.rank !== selectedRank.value) continue;
      
      const localizedName = getItemName(id);
      
      // Apply search query filter
      if (q && !id.toLowerCase().includes(q) && !localizedName.toLowerCase().includes(q)) continue;
      
      list.push({
        id,
        name: localizedName,
        emoji: item.emoji,
        rank: item.rank || 'common',
        file: file,
        data: item
      });
    }
  }
  
  return list.sort((a, b) => a.name.localeCompare(b.name));
});
</script>

<style scoped>
.item-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 1010;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  display: flex;
  justify-content: center;
  align-items: center;
}

.item-modal-dialog {
  background: var(--md-sys-color-surface-container);
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 28px; /* M3 Dialog border radius */
  box-shadow: 0 12px 32px rgba(0,0,0,0.5);
  width: 700px;
  max-width: 90vw;
  height: 85vh;
  max-height: 750px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.item-modal-header {
  padding: 24px 24px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
}

.item-modal-header h3 {
  margin: 0;
  font-size: 1.3rem;
  color: var(--md-sys-color-on-surface);
}

.close-btn {
  padding: 6px 12px;
  border-radius: 50%;
  font-size: 0.9rem;
}

.item-modal-filters {
  padding: 16px 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
  background: var(--md-sys-color-surface-container-low);
}

.search-input {
  width: 100%;
}

.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.filter-chip {
  background: var(--md-sys-color-surface-container-low);
  border: 1px solid var(--md-sys-color-outline);
  color: var(--md-sys-color-on-surface);
  border-radius: 8px;
  padding: 4px 12px;
  font-size: 0.78rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-chip.active {
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
  border-color: var(--md-sys-color-primary);
}

.category-chip {
  opacity: 0.8;
  font-size: 0.72rem;
  text-transform: capitalize;
}

.item-modal-grid {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 12px;
  align-content: start;
}

.item-grid-card {
  background: var(--md-sys-color-surface-container-high);
  border: 1.5px solid var(--md-sys-color-outline-variant);
  border-radius: 16px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
  position: relative;
  overflow: hidden;
}

.item-grid-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.25);
}

/* Rarity colors on border */
.item-grid-card.rarity-common { border-color: rgba(148, 163, 184, 0.35); }
.item-grid-card.rarity-uncommon { border-color: rgba(34, 197, 94, 0.45); }
.item-grid-card.rarity-rare { border-color: rgba(59, 130, 246, 0.45); }
.item-grid-card.rarity-epic { border-color: rgba(168, 85, 247, 0.5); }
.item-grid-card.rarity-mystical { border-color: rgba(236, 72, 153, 0.5); }
.item-grid-card.rarity-legendary { border-color: rgba(234, 179, 8, 0.6); }
.item-grid-card.rarity-mythical { border-color: rgba(239, 68, 68, 0.7); }

.item-grid-card.rarity-common:hover { box-shadow: 0 0 10px rgba(148, 163, 184, 0.3); }
.item-grid-card.rarity-uncommon:hover { box-shadow: 0 0 10px rgba(34, 197, 94, 0.3); }
.item-grid-card.rarity-rare:hover { box-shadow: 0 0 10px rgba(59, 130, 246, 0.3); }
.item-grid-card.rarity-epic:hover { box-shadow: 0 0 10px rgba(168, 85, 247, 0.3); }
.item-grid-card.rarity-mystical:hover { box-shadow: 0 0 10px rgba(236, 72, 153, 0.3); }
.item-grid-card.rarity-legendary:hover { box-shadow: 0 0 12px rgba(234, 179, 8, 0.4); }
.item-grid-card.rarity-mythical:hover { box-shadow: 0 0 12px rgba(239, 68, 68, 0.4); }

.item-grid-emoji {
  font-size: 1.8rem;
  margin-bottom: 6px;
}

.item-grid-name {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
  line-height: 1.2;
  margin-bottom: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  height: 28px;
}

.item-grid-id {
  font-size: 0.62rem;
  color: var(--md-sys-color-outline);
  word-break: break-all;
  line-height: 1.1;
  height: 22px;
  overflow: hidden;
}

.item-grid-badge {
  font-size: 0.55rem;
  text-transform: uppercase;
  font-weight: 700;
  background: var(--md-sys-color-outline-variant);
  color: var(--md-sys-color-on-surface);
  padding: 1px 6px;
  border-radius: 4px;
  margin-top: 6px;
}

.no-items-message {
  grid-column: 1 / -1;
  text-align: center;
  padding: 40px;
  color: var(--md-sys-color-outline);
  font-size: 0.9rem;
}
</style>
