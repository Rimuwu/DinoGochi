<template>
  <div class="canvas-container">
    
    <!-- LEFT SIDEBAR: Config Browser -->
    <div class="ui-panel left-sidebar" v-if="sidebarOpen">
      <div class="panel-header">
        <span>🎮 DinoGochi Configs</span>
        <button class="secondary" @click="sidebarOpen = false">◀</button>
      </div>
      
      <div class="panel-content flex flex-col gap-2">
        <input 
          v-model="searchQuery" 
          type="text" 
          placeholder="Search configs or items..." 
          class="mb-2"
        />
        
        <!-- Category Selector -->
        <select v-model="activeCategory" class="mb-2">
          <option value="items">🎒 Items ({{ totalItemsCount }} total)</option>
          <option value="quests">📜 Quests ({{ totalQuestsCount }})</option>
          <option value="mobs">👾 Mobs ({{ totalMobsCount }})</option>
          <option value="journey">🧭 Journeys / Trips ({{ totalJourneyEventsCount }})</option>
          <option value="achievements">🏆 Achievements ({{ totalAchievementsCount }})</option>
          <option value="shops">🛒 Shops (Premium & Super)</option>
          <option value="strategies">⚔️ Battle Strategies</option>
          <option value="settings">⚙️ Settings</option>
        </select>
        
        <div class="flex justify-between mb-2 gap-2">
          <button class="secondary text-xs" style="flex: 1;" @click="spawnAllInCategory">Spawn All</button>
          <button class="secondary text-xs" style="flex: 1;" @click="clearAllInCategory">Clear Canvas</button>
        </div>

        <button 
          v-if="activeCategory === 'items'" 
          class="text-xs mb-2 font-bold" 
          @click="createNewItem"
        >
          ➕ Create New Item
        </button>

        <!-- List of items in active category -->
        <div class="flex flex-col gap-1 overflow-y-auto" style="max-height: 50vh;">
          <div 
            v-for="item in filteredCategoryItems" 
            :key="item.id"
            class="flex items-center justify-between p-2 rounded cursor-pointer"
            :class="{
              'bg-purple-950/20 border border-purple-500/20': isNodeSpawned(item.id),
              'hover:bg-zinc-800/40': !isNodeSpawned(item.id)
            }"
            @click="toggleNodeOnCanvas(item)"
          >
            <span class="text-sm truncate" :title="item.label">
              {{ item.emoji || '🔹' }} {{ item.label }}
            </span>
            <span class="text-xs text-muted">
              {{ isNodeSpawned(item.id) ? 'Focus 🔍' : 'Spawn ➕' }}
            </span>
          </div>
        </div>
      </div>
    </div>
    
    <button 
      class="ui-panel" 
      style="top: 20px; left: 20px; padding: 10px 14px; border-radius: 8px;" 
      v-if="!sidebarOpen" 
      @click="sidebarOpen = true"
    >
      ▶ Show Sidebar
    </button>



    <!-- TOOLBAR PANEL -->
    <div class="ui-panel toolbar-panel">
      <span class="text-xs font-bold text-muted">Zoom: {{ Math.round(scale * 100) }}%</span>
      <button class="secondary" style="padding: 4px 10px;" @click="scale = Math.min(3.0, scale + 0.1)">＋</button>
      <button class="secondary" style="padding: 4px 10px;" @click="scale = Math.max(0.15, scale - 0.1)">－</button>
      <button class="secondary" @click="resetView">Center</button>
      <button class="secondary" @click="runAutoLayout">Auto Grid</button>
      <button @click="saveAllLayouts" class="font-bold">💾 Save Layout</button>
      <button @click="clearWholeCanvas" class="danger" style="margin-left: 8px;">🗑️ Clear Canvas</button>
    </div>

    <!-- MAIN INFINITE CANVAS -->
    <InfiniteCanvas v-model:scale="scale" v-model:pan="pan">
      
      <!-- SVG Overlay for drawing connections -->
      <template #svg>
        <svg class="connections-svg">
          <!-- Connection Paths -->
          <path 
            v-for="(link, idx) in computedConnections" 
            :key="idx"
            :d="link.path"
            :class="{ 'active-link': selectedNodeId === link.sourceId || selectedNodeId === link.targetId }"
            :title="`Connection from ${link.sourceLabel} to ${link.targetLabel}`"
          />
        </svg>
      </template>

      <!-- Render Spawned Config Nodes -->
      <ConfigCard 
        v-for="node in nodes" 
        :key="node.id"
        :node="node"
        :scale="scale"
        :selected="selectedNodeId === node.id"
        :all-items="configs.items"
        :localization="configs.localization"
        @update:position="updateNodePosition(node.id, $event)"
        @click="selectNode(node)"
        @contextmenu="showContextMenu($event, node)"
        @save="saveNode"
        @cancel="closeEditor"
        @pick-item="pickItem"
      />

    </InfiniteCanvas>

    <!-- Context Menu Overlay (to dismiss click) -->
    <div 
      v-if="contextMenu.visible" 
      class="context-menu-overlay" 
      @click="closeContextMenu" 
      @contextmenu.prevent="closeContextMenu"
    ></div>

    <!-- Material Design 3 Styled Context Menu -->
    <div 
      v-if="contextMenu.visible" 
      class="context-menu"
      :style="{ top: `${contextMenu.y}px`, left: `${contextMenu.x}px` }"
    >
      <div class="context-menu-item" @click="editContextMenuNode">
        <span class="context-menu-icon">✏️</span>
        <span>Редактировать</span>
      </div>
      <div class="context-menu-item" @click="focusContextMenuNode">
        <span class="context-menu-icon">🔍</span>
        <span>Фокусировать</span>
      </div>
      <div class="context-menu-divider"></div>
      <div class="context-menu-item danger" @click="deleteContextMenuNode">
        <span class="context-menu-icon">🗑️</span>
        <span>Удалить с холста</span>
      </div>
    </div>

    <!-- Item Picker Grid Modal -->
    <ItemPickerModal 
      :visible="pickerState.visible"
      :all-items="configs.items"
      :localization="configs.localization"
      @select="handleItemPickerSelect"
      @close="pickerState.visible = false"
    />

    <!-- Visual status alert notifications -->
    <div 
      v-if="statusMessage" 
      class="ui-panel" 
      style="bottom: 80px; left: 50%; transform: translateX(-50%); padding: 12px 24px; border-color: #22c55e; background: rgba(22, 163, 74, 0.2);"
    >
      {{ statusMessage }}
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue';
import InfiniteCanvas from './components/InfiniteCanvas.vue';
import ConfigCard from './components/ConfigCard.vue';
import ItemPickerModal from './components/ItemPickerModal.vue';

// Global variables & state caches
const scale = ref(0.75);
const pan = ref({ x: window.innerWidth / 2 - 200, y: window.innerHeight / 2 - 250 });

const sidebarOpen = ref(true);
const selectedNodeId = ref(null);
const searchQuery = ref('');
const activeCategory = ref('items');
const statusMessage = ref('');

const configs = reactive({
  settings: {},
  premium_shop: {},
  super_shop: {},
  quests: [],
  mobs: {},
  journey: {},
  combat_strategies: {},
  achievements: {},
  items: {},
  localization: {}
});

const nodes = ref([]);
const layout = ref({});

// Item Picker Modal State
const pickerState = reactive({
  visible: false,
  resolve: null,
  reject: null
});

const pickItem = (callback) => {
  pickerState.visible = true;
  pickerState.resolve = (itemId) => {
    callback(itemId);
    pickerState.visible = false;
  };
};

const handleItemPickerSelect = (itemId) => {
  if (pickerState.resolve) {
    pickerState.resolve(itemId);
  }
};

// Context Menu state & helpers
const contextMenu = reactive({
  visible: false,
  x: 0,
  y: 0,
  node: null
});

const showContextMenu = (e, node) => {
  contextMenu.visible = true;
  contextMenu.x = e.clientX;
  contextMenu.y = e.clientY;
  contextMenu.node = node;
};

const closeContextMenu = () => {
  contextMenu.visible = false;
  contextMenu.node = null;
};

const editContextMenuNode = () => {
  if (contextMenu.node) {
    selectNode(contextMenu.node);
  }
  closeContextMenu();
};

const focusContextMenuNode = () => {
  if (contextMenu.node) {
    pan.value = {
      x: window.innerWidth / 2 - contextMenu.node.x * scale.value,
      y: window.innerHeight / 2 - contextMenu.node.y * scale.value
    };
  }
  closeContextMenu();
};

const deleteContextMenuNode = () => {
  if (contextMenu.node) {
    removeNode(contextMenu.node.id);
  }
  closeContextMenu();
};

const removeNode = (nodeId) => {
  nodes.value = nodes.value.filter(n => n.id !== nodeId);
  if (selectedNodeId.value === nodeId) {
    closeEditor();
  }
  showStatus('Карточка удалена с холста.');
};

// Get selected node
const selectedNode = computed(() => {
  return nodes.value.find(n => n.id === selectedNodeId.value) || null;
});

// Translation helpers
const t = (path) => {
  if (!configs.localization || !configs.localization.ru) return path;
  const parts = path.split('.');
  let current = configs.localization.ru;
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

const getMobName = (mobId) => {
  const name = t(`mobs.${mobId}.name`);
  if (name !== `mobs.${mobId}.name`) return name;
  return mobId;
};

const getMobEmoji = (mobId) => {
  const emoji = t(`mobs.${mobId}.emoji`);
  if (emoji !== `mobs.${mobId}.emoji`) return emoji;
  return '👾';
};

const getAchievementName = (achId) => {
  const name = t(`achievements.${achId}.name`);
  if (name !== `achievements.${achId}.name`) return name;
  return achId;
};

const translateQuestType = (type) => {
  const map = {
    get: 'Принести предмет',
    feed: 'Покормить динозавра',
    collecting: 'Сбор еды',
    hunting: 'Охота',
    fishing: 'Рыбалка'
  };
  return map[type] || type;
};

// Global Hotkeys for Deletion
const handleKeyDown = (e) => {
  if (e.key === 'Delete' || e.key === 'Backspace') {
    if (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA' || document.activeElement.tagName === 'SELECT') {
      return;
    }
    if (selectedNodeId.value) {
      removeNode(selectedNodeId.value);
    }
  }
};

// Load config data on mount
onMounted(async () => {
  window.addEventListener('keydown', handleKeyDown);
  try {
    const res = await fetch('/api/configs');
    const data = await res.json();
    Object.assign(configs, data);
    
    // Load layout positions
    const layoutRes = await fetch('/api/layout');
    layout.value = await layoutRes.json();
    
    // Spawn a few default nodes to make it look interesting on start
    spawnDefaultNodes();
  } catch (err) {
    console.error('Failed to load configs:', err);
    showStatus('Failed to load configuration files from backend!');
  }
});

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeyDown);
});

const spawnDefaultNodes = () => {
  // Spawn settings card
  spawnNode({ id: 'settings', label: 'Глобальные настройки', type: 'settings', data: configs.settings });
  
  // Spawn first 2 quests if present
  if (configs.quests && configs.quests.length > 0) {
    configs.quests.slice(0, 2).forEach((q, idx) => {
      spawnNode({ 
        id: `quest_${idx}`, 
        label: `Квест: ${translateQuestType(q.type)} (Сложность ${q.complexity})`, 
        type: 'quest', 
        data: q 
      });
    });
  }
  
  // Spawn combat strategies
  if (configs.combat_strategies && configs.combat_strategies.strategies) {
    for (const key in configs.combat_strategies.strategies) {
      spawnNode({ 
        id: `strategy_${key}`, 
        label: `Стратегия: ${key === 'carry' ? 'Керри' : key === 'tank' ? 'Танк' : 'Поддержка'}`, 
        type: 'strategy', 
        data: configs.combat_strategies.strategies[key] 
      });
    }
  }
};

// Spawn helper
const spawnNode = (nodeSpec, forceCenter = false) => {
  if (nodes.value.some(n => n.id === nodeSpec.id)) {
    if (forceCenter) {
      const existingNode = nodes.value.find(n => n.id === nodeSpec.id);
      pan.value = {
        x: window.innerWidth / 2 - existingNode.x * scale.value,
        y: window.innerHeight / 2 - existingNode.y * scale.value
      };
    }
    return;
  }
  
  // Resolve coordinate layout
  let x = 0, y = 0;
  if (forceCenter) {
    x = Math.round((window.innerWidth / 2 - pan.value.x) / scale.value);
    y = Math.round((window.innerHeight / 2 - pan.value.y) / scale.value) + (nodes.value.length % 5) * 40;
    layout.value[nodeSpec.id] = { x, y };
  } else if (layout.value[nodeSpec.id]) {
    x = layout.value[nodeSpec.id].x;
    y = layout.value[nodeSpec.id].y;
  } else {
    // Spawn at center of view by default
    x = Math.round((window.innerWidth / 2 - pan.value.x) / scale.value);
    y = Math.round((window.innerHeight / 2 - pan.value.y) / scale.value) + (nodes.value.length % 5) * 40;
    layout.value[nodeSpec.id] = { x, y };
  }
  
  const spawned = {
    ...nodeSpec,
    x,
    y
  };
  
  nodes.value.push(spawned);
  
  // Automatically split settings keys if spawning master settings card!
  if (spawned.id === 'settings') {
    const keys = Object.keys(configs.settings);
    keys.forEach((k, idx) => {
      const subId = `settings_${k}`;
      if (!isNodeSpawned(subId)) {
        const subX = spawned.x + 380;
        const subY = spawned.y + (idx * 200) - ((keys.length - 1) * 100);
        layout.value[subId] = { x: subX, y: subY };
        
        spawnNode({
          id: subId,
          label: `Параметр: ${k}`,
          type: 'settings_sub',
          data: configs.settings[k]
        });
      }
    });
  }
  
  // Recursively spawn dependencies (items, etc.)
  spawnDependencies(spawned);
};

const spawnDependencies = (node) => {
  const deps = [];
  
  if (node.type === 'quest' && node.data.data?.items) {
    node.data.data.items.forEach(id => { if (id) deps.push(id); });
  } else if (node.type === 'mob' && node.data.loot) {
    node.data.loot.forEach(id => { if (id) deps.push(id); });
  } else if (node.type === 'journey' && node.data.outcomes) {
    node.data.outcomes.forEach(outcome => {
      if (outcome.items_add) {
        outcome.items_add.forEach(itm => { if (itm.item_id) deps.push(itm.item_id); });
      }
    });
  } else if (node.type === 'shop_premium' && node.data.items) {
    node.data.items.forEach(id => { if (id) deps.push(id); });
  } else if (node.type === 'shop_super' && node.data.items) {
    node.data.items.forEach(id => { if (id) deps.push(id); });
  } else if (node.type === 'achievement' && node.data.award?.items) {
    node.data.award.items.forEach(itm => { if (itm.item_id) deps.push(itm.item_id); });
  } else if (node.type === 'settings' && node.data.starter_items) {
    node.data.starter_items.forEach(itm => { if (itm.item_id) deps.push(itm.item_id); });
  } else if (node.type === 'settings_sub') {
    const scanForDeps = (val) => {
      if (typeof val === 'string') {
        for (const file in configs.items) {
          if (configs.items[file][val]) {
            deps.push(val);
            break;
          }
        }
      } else if (Array.isArray(val)) {
        val.forEach(v => scanForDeps(v));
      } else if (typeof val === 'object' && val !== null) {
        Object.keys(val).forEach(k => {
          if (k === 'item_id' && typeof val[k] === 'string') {
            deps.push(val[k]);
          } else {
            scanForDeps(val[k]);
          }
        });
      }
    };
    scanForDeps(node.data);
  }
  
  const uniqueDeps = [...new Set(deps)];
  
  uniqueDeps.forEach((depId, idx) => {
    // Find item
    let foundItem = null;
    let foundFile = '';
    for (const file in configs.items) {
      if (configs.items[file][depId]) {
        foundItem = configs.items[file][depId];
        foundFile = file;
        break;
      }
    }
    
    if (foundItem) {
      if (!isNodeSpawned(depId)) {
        // Place to the right of parent card
        const x = node.x + 380;
        const y = node.y + (idx * 180) - ((uniqueDeps.length - 1) * 80);
        
        layout.value[depId] = { x, y };
        spawnNode({
          id: depId,
          label: getItemName(depId),
          type: 'item',
          emoji: foundItem.emoji,
          file_name: foundFile,
          data: foundItem
        });
      }
    }
  });
};

const isNodeSpawned = (id) => {
  return nodes.value.some(n => n.id === id);
};

const toggleNodeOnCanvas = (item) => {
  const existingNode = nodes.value.find(n => n.id === item.id);
  if (existingNode) {
    // Focus view onto existing node
    pan.value = {
      x: window.innerWidth / 2 - existingNode.x * scale.value,
      y: window.innerHeight / 2 - existingNode.y * scale.value
    };
    selectedNodeId.value = existingNode.id;
  } else {
    // Spawn node in center of screen
    spawnNode({
      id: item.id,
      label: item.label,
      type: item.type,
      data: item.data,
      emoji: item.emoji,
      file_name: item.file_name
    }, true);
  }
};

const updateNodePosition = (id, pos) => {
  const node = nodes.value.find(n => n.id === id);
  if (node) {
    const dx = pos.x - node.x;
    const dy = pos.y - node.y;
    
    // Shift parent position
    node.x = pos.x;
    node.y = pos.y;
    layout.value[id] = { x: pos.x, y: pos.y };
    
    // Identify dependent children of this node that are spawned on the canvas
    const childIds = [];
    
    if (id === 'settings') {
      Object.keys(configs.settings).forEach(k => childIds.push(`settings_${k}`));
    }
    if (node.type === 'quest' && node.data.data?.items) {
      node.data.data.items.forEach(cId => { if (cId) childIds.push(cId); });
    }
    if (node.type === 'mob' && node.data.loot) {
      node.data.loot.forEach(cId => { if (cId) childIds.push(cId); });
    }
    if (node.type === 'journey' && node.data.outcomes) {
      node.data.outcomes.forEach(out => {
        if (out.items_add) {
          out.items_add.forEach(itm => { if (itm.item_id) childIds.push(itm.item_id); });
        }
      });
    }
    if ((node.type === 'shop_premium' || node.type === 'shop_super') && node.data.items) {
      node.data.items.forEach(cId => { if (cId) childIds.push(cId); });
    }
    if (node.type === 'achievement' && node.data.award?.items) {
      node.data.award.items.forEach(itm => { if (itm.item_id) childIds.push(itm.item_id); });
    }
    if (node.id === 'settings_starter_items' && node.data) {
      node.data.forEach(itm => { if (itm.item_id) childIds.push(itm.item_id); });
    }
    
    // Translate children positions together
    childIds.forEach(childId => {
      const child = nodes.value.find(n => n.id === childId);
      if (child && childId !== id) {
        child.x += dx;
        child.y += dy;
        layout.value[childId] = { x: child.x, y: child.y };
      }
    });
  }
};

const selectNode = (node) => {
  selectedNodeId.value = node.id;
};

const closeEditor = () => {
  selectedNodeId.value = null;
};

const resetView = () => {
  scale.value = 1.0;
  pan.value = {
    x: window.innerWidth / 2 - 150,
    y: window.innerHeight / 2 - 200
  };
};

const runAutoLayout = () => {
  const categories = ['settings', 'settings_sub', 'item', 'quest', 'mob', 'journey', 'achievement', 'shop_premium', 'shop_super', 'strategy'];
  const colWidth = 350;
  const rowHeight = 220;
  
  categories.forEach((cat, colIdx) => {
    const catNodes = nodes.value.filter(n => n.type === cat);
    catNodes.forEach((node, rowIdx) => {
      const x = colIdx * colWidth - (categories.length * colWidth) / 2;
      const y = rowIdx * rowHeight - 200;
      node.x = x;
      node.y = y;
      layout.value[node.id] = { x, y };
    });
  });
  showStatus('Grid auto-layout finished!');
};

// Config saves
const saveNode = async (updatedNode) => {
  try {
    const idx = nodes.value.findIndex(n => n.id === updatedNode.id);
    if (idx !== -1) {
      nodes.value[idx] = updatedNode;
    }
    
    layout.value[updatedNode.id] = { x: updatedNode.x, y: updatedNode.y };
    
    let savePayload = { type: updatedNode.type, data: null };
    
    if (updatedNode.type === 'item') {
      const fileName = updatedNode.file_name || 'items.json';
      if (!configs.items[fileName]) {
        configs.items[fileName] = {};
      }
      configs.items[fileName][updatedNode.id] = updatedNode.data;
      
      savePayload = {
        type: 'item',
        file_name: fileName,
        data: configs.items[fileName]
      };
      
      if (updatedNode.isNew) {
        updatedNode.isNew = false;
      }
    } else if (updatedNode.type === 'settings') {
      configs.settings = updatedNode.data;
      savePayload = { type: 'settings', data: configs.settings };
    } else if (updatedNode.type === 'settings_sub') {
      // Map parameter back to settings dictionary
      const paramKey = updatedNode.id.replace('settings_', '');
      configs.settings[paramKey] = updatedNode.data;
      savePayload = { type: 'settings', data: configs.settings };
    } else if (updatedNode.type === 'quest') {
      const qIdx = configs.quests.findIndex(q => q.type === updatedNode.data.type && q.complexity === updatedNode.data.complexity);
      if (qIdx !== -1) {
        configs.quests[qIdx] = updatedNode.data;
      } else {
        configs.quests.push(updatedNode.data);
      }
      savePayload = { type: 'quests', data: configs.quests };
    } else if (updatedNode.type === 'mob') {
      if (!configs.mobs.mobs) configs.mobs.mobs = {};
      configs.mobs.mobs[updatedNode.id] = updatedNode.data;
      savePayload = { type: 'mobs', data: configs.mobs };
    } else if (updatedNode.type === 'journey') {
      if (!configs.journey.events) configs.journey.events = {};
      configs.journey.events[updatedNode.id] = updatedNode.data;
      savePayload = { type: 'journey', data: configs.journey };
    } else if (updatedNode.type === 'achievement') {
      if (!configs.achievements.achievements) configs.achievements.achievements = {};
      configs.achievements.achievements[updatedNode.id] = updatedNode.data;
      savePayload = { type: 'achievements', data: configs.achievements };
    } else if (updatedNode.type === 'shop_premium') {
      configs.premium_shop[updatedNode.id] = updatedNode.data;
      savePayload = { type: 'premium_shop', data: configs.premium_shop };
    } else if (updatedNode.type === 'shop_super') {
      configs.super_shop[updatedNode.id] = updatedNode.data;
      savePayload = { type: 'super_shop', data: configs.super_shop };
    } else if (updatedNode.type === 'strategy') {
      if (!configs.combat_strategies.strategies) configs.combat_strategies.strategies = {};
      configs.combat_strategies.strategies[updatedNode.id.replace('strategy_', '')] = updatedNode.data;
      savePayload = { type: 'combat_strategies', data: configs.combat_strategies };
    }
    
    // Save to Disk
    const saveRes = await fetch('/api/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(savePayload)
    });
    
    const saveResult = await saveRes.json();
    if (saveResult.success) {
      showStatus(`Saved changes for ${updatedNode.label} to file!`);
    } else {
      showStatus(`Error saving to file: ${saveResult.error}`);
    }
    
    await saveAllLayouts();
    
  } catch (err) {
    console.error('Failed to save config node:', err);
    showStatus('Failed to save configuration node changes!');
  }
};

const saveAllLayouts = async () => {
  try {
    await fetch('/api/layout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(layout.value)
    });
  } catch (err) {
    console.error('Failed to save coordinates:', err);
  }
};

// Create new item spawner
const createNewItem = () => {
  const newItemId = `new_item_${Date.now().toString().slice(-4)}`;
  const spec = {
    id: newItemId,
    label: newItemId,
    type: 'item',
    file_name: 'items.json',
    isNew: true,
    data: {
      type: 'dummy',
      rank: 'common',
      cant_sell: false,
      emoji: '📦',
      image: {
        background: 'grey_bg',
        frame: 'elipse',
        icon: 'null'
      },
      groups: []
    }
  };
  
  // Center of viewport
  const canvasCenter = {
    x: Math.round((window.innerWidth / 2 - pan.value.x) / scale.value),
    y: Math.round((window.innerHeight / 2 - pan.value.y) / scale.value)
  };
  
  layout.value[spec.id] = canvasCenter;
  spawnNode(spec);
  
  selectedNodeId.value = spec.id;
};

// Notifications helper
const showStatus = (msg) => {
  statusMessage.value = msg;
  setTimeout(() => {
    statusMessage.value = '';
  }, 3500);
};

// Category items list builder
const filteredCategoryItems = computed(() => {
  const q = searchQuery.value.toLowerCase();
  const list = [];
  
  if (activeCategory.value === 'items') {
    for (const file in configs.items) {
      for (const key in configs.items[file]) {
        const itemLabel = getItemName(key);
        if (!q || key.toLowerCase().includes(q) || itemLabel.toLowerCase().includes(q) || (configs.items[file][key].type && configs.items[file][key].type.toLowerCase().includes(q))) {
          list.push({
            id: key,
            label: itemLabel,
            type: 'item',
            emoji: configs.items[file][key].emoji,
            file_name: file,
            data: configs.items[file][key]
          });
        }
      }
    }
  } else if (activeCategory.value === 'quests') {
    configs.quests.forEach((quest, idx) => {
      const label = `Квест: ${translateQuestType(quest.type)} (Сложность ${quest.complexity})`;
      if (!q || label.toLowerCase().includes(q)) {
        list.push({
          id: `quest_${idx}`,
          label: label,
          type: 'quest',
          data: quest
        });
      }
    });
  } else if (activeCategory.value === 'mobs') {
    if (configs.mobs.mobs) {
      for (const key in configs.mobs.mobs) {
        const mobLabel = getMobName(key);
        if (!q || key.toLowerCase().includes(q) || mobLabel.toLowerCase().includes(q)) {
          list.push({
            id: key,
            label: mobLabel,
            emoji: getMobEmoji(key),
            type: 'mob',
            data: configs.mobs.mobs[key]
          });
        }
      }
    }
  } else if (activeCategory.value === 'journey') {
    if (configs.journey.events) {
      for (const key in configs.journey.events) {
        if (!q || key.toLowerCase().includes(q)) {
          list.push({
            id: key,
            label: `Путешествие: ${key}`,
            type: 'journey',
            data: configs.journey.events[key]
          });
        }
      }
    }
  } else if (activeCategory.value === 'achievements') {
    if (configs.achievements.achievements) {
      for (const key in configs.achievements.achievements) {
        const achLabel = getAchievementName(key);
        if (!q || key.toLowerCase().includes(q) || achLabel.toLowerCase().includes(q)) {
          list.push({
            id: key,
            label: achLabel,
            type: 'achievement',
            data: configs.achievements.achievements[key]
          });
        }
      }
    }
  } else if (activeCategory.value === 'shops') {
    for (const key in configs.premium_shop) {
      const label = `Донат: ${key}`;
      if (!q || label.toLowerCase().includes(q)) {
        list.push({
          id: key,
          label: label,
          type: 'shop_premium',
          data: configs.premium_shop[key]
        });
      }
    }
    for (const key in configs.super_shop) {
      const label = `Супер-магазин: ${key}`;
      if (!q || label.toLowerCase().includes(q)) {
        list.push({
          id: key,
          label: label,
          type: 'shop_super',
          data: configs.super_shop[key]
        });
      }
    }
  } else if (activeCategory.value === 'strategies') {
    if (configs.combat_strategies.strategies) {
      for (const key in configs.combat_strategies.strategies) {
        const label = `Стратегия: ${key === 'carry' ? 'Керри' : key === 'tank' ? 'Танк' : 'Поддержка'}`;
        if (!q || label.toLowerCase().includes(q)) {
          list.push({
            id: `strategy_${key}`,
            label: label,
            type: 'strategy',
            data: configs.combat_strategies.strategies[key]
          });
        }
      }
    }
  } else if (activeCategory.value === 'settings') {
    list.push({
      id: 'settings',
      label: 'Глобальные настройки',
      type: 'settings',
      data: configs.settings
    });
  }
  
  return list;
});

// Spawn/Clear actions in sidebar
const spawnAllInCategory = () => {
  filteredCategoryItems.value.forEach(item => {
    spawnNode(item);
  });
  showStatus(`Spawned all visible ${activeCategory.value} items on canvas!`);
};

const clearAllInCategory = () => {
  const idsToRemove = filteredCategoryItems.value.map(item => item.id);
  
  if (activeCategory.value === 'settings') {
    idsToRemove.push('settings');
    Object.keys(configs.settings).forEach(k => {
      idsToRemove.push(`settings_${k}`);
    });
  }
  
  nodes.value = nodes.value.filter(n => !idsToRemove.includes(n.id) && !(n.type === 'settings_sub' && activeCategory.value === 'settings'));
  showStatus(`Очищена категория ${activeCategory.value} с холста.`);
};

const clearWholeCanvas = () => {
  nodes.value = [];
  closeEditor();
  showStatus('Холст полностью очищен.');
};

// Count aggregators for sidebar labels
const totalItemsCount = computed(() => {
  let count = 0;
  for (const f in configs.items) {
    count += Object.keys(configs.items[f]).length;
  }
  return count;
});
const totalQuestsCount = computed(() => configs.quests.length);
const totalMobsCount = computed(() => configs.mobs.mobs ? Object.keys(configs.mobs.mobs).length : 0);
const totalJourneyEventsCount = computed(() => configs.journey.events ? Object.keys(configs.journey.events).length : 0);
const totalAchievementsCount = computed(() => configs.achievements.achievements ? Object.keys(configs.achievements.achievements).length : 0);

// Connections drawing engine
const computedConnections = computed(() => {
  const links = [];
  const nodesMap = {};
  nodes.value.forEach(node => {
    nodesMap[node.id] = node;
  });
  
  nodes.value.forEach(node => {
    const addLink = (targetId) => {
      if (nodesMap[targetId]) {
        const srcNode = node;
        const tgtNode = nodesMap[targetId];
        
        const x_src = srcNode.x + 310; // M3 width is 310
        const y_src = srcNode.y + 45;
        const x_dst = tgtNode.x;
        const y_dst = tgtNode.y + 45;
        
        const path = `M ${x_src} ${y_src} C ${(x_src + x_dst) / 2} ${y_src}, ${(x_src + x_dst) / 2} ${y_dst}, ${x_dst} ${y_dst}`;
        
        links.push({
          path,
          sourceId: srcNode.id,
          targetId: tgtNode.id,
          sourceLabel: srcNode.label,
          targetLabel: tgtNode.label
        });
      }
    };
    
    // Connect Settings master to parameter child nodes
    if (node.id === 'settings') {
      Object.keys(configs.settings).forEach(k => {
        addLink(`settings_${k}`);
      });
    }
    
    // Connect Settings sub-nodes to Items recursively (starter_items, change_rarity, etc.)
    if (node.type === 'settings_sub') {
      const scanForItems = (val) => {
        if (typeof val === 'string') {
          if (nodesMap[val] && nodesMap[val].type === 'item') {
            addLink(val);
          }
        } else if (Array.isArray(val)) {
          val.forEach(v => scanForItems(v));
        } else if (typeof val === 'object' && val !== null) {
          Object.keys(val).forEach(k => {
            if (k === 'item_id' && typeof val[k] === 'string') {
              if (nodesMap[val[k]]) addLink(val[k]);
            } else {
              scanForItems(val[k]);
            }
          });
        }
      };
      scanForItems(node.data);
    }

    // Connect Quests -> Target items
    if (node.type === 'quest' && node.data.data?.items) {
      node.data.data.items.forEach(itemId => {
        if (itemId) addLink(itemId);
      });
    }
    
    // Connect Mobs -> Drops (loot list)
    if (node.type === 'mob' && node.data.loot) {
      node.data.loot.forEach(itemId => {
        if (itemId) addLink(itemId);
      });
    }
    
    // Connect Journey Events -> Drop Items
    if (node.type === 'journey' && node.data.outcomes) {
      node.data.outcomes.forEach(outcome => {
        if (outcome.items_add) {
          outcome.items_add.forEach(itm => {
            if (itm.item_id) addLink(itm.item_id);
          });
        }
      });
    }

    // Connect Shop Premium -> Included items
    if (node.type === 'shop_premium' && node.data.items) {
      node.data.items.forEach(itemId => {
        if (itemId) addLink(itemId);
      });
    }

    // Connect Shop Super -> Included items
    if (node.type === 'shop_super' && node.data.items) {
      node.data.items.forEach(itemId => {
        if (itemId) addLink(itemId);
      });
    }

    // Connect Achievements -> Reward Items
    if (node.type === 'achievement' && node.data.award?.items) {
      node.data.award.items.forEach(itm => {
        if (itm.item_id) addLink(itm.item_id);
      });
    }
  });
  
  return links;
});
</script>
