<template>
  <div 
    class="node-card"
    :class="[
      `rarity-${getRarity(node)}`,
      { selected: selected }
    ]"
    :style="{
      left: `${node.x}px`,
      top: `${node.y}px`,
      zIndex: dragging ? 100 : (selected ? 50 : 5)
    }"
    @mousedown.stop="startDrag"
    @click.stop="$emit('click')"
    @contextmenu.prevent="$emit('contextmenu', $event)"
  >
    <div class="card-header">
      <span class="flex items-center gap-2">
        <span class="text-sm font-bold">{{ getEmoji(node) }}</span>
        <span class="card-title" :title="node.label">{{ node.label }}</span>
      </span>
      <span class="card-badge" :style="{ background: getTypeColor(node.type) }">
        {{ node.type }}
      </span>
    </div>
    
    <div class="card-content" :class="{ 'edit-mode-content': selected }">
      
      <!-- ==================== READ-ONLY VIEW ==================== -->
      <template v-if="!selected">
        <template v-if="node.type === 'item'">
          <div class="card-field">
            <span>Type:</span>
            <span class="card-field-val">{{ node.data.type || 'dummy' }}</span>
          </div>
          <div class="card-field">
            <span>Rank:</span>
            <span class="card-field-val" :style="{ color: getRarityColor(getRarity(node)) }">
              {{ translateRank(getRarity(node)) }}
            </span>
          </div>

          <!-- Render extra keys dynamically -->
          <div v-for="(val, key) in node.data" :key="key">
            <div v-if="!['type', 'rank', 'emoji', 'image', 'id', 'groups', 'abilities', 'ns_craft'].includes(key) && val !== null && val !== ''" class="card-field">
              <span class="text-muted text-xs capitalize">{{ key.replace('_', ' ') }}:</span>
              <span class="card-field-val">{{ formatValue(val) }}</span>
            </div>
          </div>
          
          <!-- Grouped Abilities -->
          <div v-if="node.data.abilities && Object.keys(node.data.abilities).length > 0" class="card-grouped-section">
            <div class="card-grouped-header">⚡ Характеристики:</div>
            <div class="card-grouped-items flex-col" style="gap: 4px; padding: 6px; width: 100%;">
              <div v-for="(v, k) in node.data.abilities" :key="k" class="card-field w-full">
                <span class="text-xs text-muted">{{ k }}:</span>
                <span class="card-field-val text-xs">{{ v }}</span>
              </div>
            </div>
          </div>

          <!-- Grouped ns_craft -->
          <div v-if="node.data.ns_craft && Object.keys(node.data.ns_craft).length > 0" class="card-grouped-section">
            <div class="card-grouped-header">🔨 Настольный крафт:</div>
            <div class="card-grouped-items flex-col" style="gap: 4px; padding: 6px; width: 100%;">
              <div v-for="(v, k) in node.data.ns_craft" :key="k" class="card-field w-full">
                <span class="text-xs text-muted">{{ k }}:</span>
                <span class="card-field-val text-xs">{{ v.materials?.map(m => `${m.count}x ${m.item_id}`).join(', ') }}</span>
              </div>
            </div>
          </div>
        </template>

        <template v-else-if="node.type === 'quest'">
          <div class="card-field">
            <span>Type:</span>
            <span class="card-field-val">{{ node.data.type }}</span>
          </div>
          <div class="card-field">
            <span>Complexity:</span>
            <span class="card-field-val">⭐ {{ node.data.complexity }}</span>
          </div>
          <div class="card-field" v-if="node.data.reward && node.data.reward.coins">
            <span>Coins:</span>
            <span class="card-field-val">
              {{ node.data.reward.coins.min }}-{{ node.data.reward.coins.max }}
            </span>
          </div>
          
          <!-- Grouped Required Items -->
          <div v-if="node.data.data?.items && node.data.data.items.length > 0" class="card-grouped-section">
            <div class="card-grouped-header">📋 Требуемые предметы:</div>
            <div class="card-grouped-items">
              <div v-for="itemId in node.data.data.items" :key="itemId" class="card-grouped-item">
                <span>{{ getItemEmoji(itemId) }}</span>
                <span class="truncate" style="max-width: 140px;">{{ getItemName(itemId) }}</span>
              </div>
            </div>
          </div>
        </template>

        <template v-else-if="node.type === 'mob'">
          <div class="card-field" v-if="node.data.mobs_default_stats && node.data.mobs_default_stats.hp">
            <span>HP:</span>
            <span class="card-field-val">
              {{ node.data.mobs_default_stats.hp.min }}-{{ node.data.mobs_default_stats.hp.max }}
            </span>
          </div>
          <div class="card-field" v-if="node.data.mobs_default_stats && node.data.mobs_default_stats.damage">
            <span>Dmg:</span>
            <span class="card-field-val">
              {{ node.data.mobs_default_stats.damage.min }}-{{ node.data.mobs_default_stats.damage.max }}
            </span>
          </div>
          
          <!-- Grouped Drops -->
          <div v-if="node.data.loot && node.data.loot.length > 0" class="card-grouped-section">
            <div class="card-grouped-header">⚔️ Возможный дроп:</div>
            <div class="card-grouped-items">
              <div v-for="itemId in node.data.loot" :key="itemId" class="card-grouped-item">
                <span>{{ getItemEmoji(itemId) }}</span>
                <span class="truncate" style="max-width: 140px;">{{ getItemName(itemId) }}</span>
              </div>
            </div>
          </div>
        </template>

        <template v-else-if="node.type === 'journey'">
          <div class="card-field">
            <span>Chance:</span>
            <span class="card-field-val">{{ node.data.chance_config?.type }} ({{ node.data.chance_config?.base || node.data.chance_config?.min }})</span>
          </div>
          
          <!-- Grouped Outcomes Rewards -->
          <div v-if="node.data.outcomes && node.data.outcomes.length > 0" class="card-grouped-section">
            <div class="card-grouped-header">🗺️ Награды за события:</div>
            <div class="card-grouped-items flex-col" style="gap: 8px;">
              <div v-for="(outcome, oIdx) in node.data.outcomes" :key="oIdx" class="flex flex-col gap-1 w-full">
                <div v-if="outcome.items_add && outcome.items_add.length > 0" class="text-xs text-muted font-bold">
                  Событие '{{ outcome.story_key || oIdx + 1 }}':
                </div>
                <div class="flex flex-wrap gap-1">
                  <div v-for="(itm, iIdx) in outcome.items_add" :key="iIdx" class="card-grouped-item">
                    <span v-if="itm.item_id">{{ getItemEmoji(itm.item_id) }} {{ getItemName(itm.item_id) }} ({{ Math.round(itm.chance * 100) }}%)</span>
                    <span v-else-if="itm.group">📦 {{ itm.group }} ({{ Math.round(itm.chance * 100) }}%)</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>

        <template v-else-if="node.type === 'achievement'">
          <div class="card-field">
            <span>Type:</span>
            <span class="card-field-val">{{ node.data.type }}</span>
          </div>
          <div class="card-field">
            <span>Secret:</span>
            <span class="card-field-val">{{ node.data.secret ? 'Yes 🤫' : 'No' }}</span>
          </div>
          
          <!-- Grouped Award Items -->
          <div v-if="node.data.award?.items && node.data.award.items.length > 0" class="card-grouped-section">
            <div class="card-grouped-header">🏆 Награды (предметы):</div>
            <div class="card-grouped-items">
              <div v-for="itm in node.data.award.items" :key="itm.item_id" class="card-grouped-item">
                <span>{{ getItemEmoji(itm.item_id) }}</span>
                <span class="truncate" style="max-width: 140px;">{{ getItemName(itm.item_id) }} x{{ itm.count }}</span>
              </div>
            </div>
          </div>
        </template>

        <template v-else-if="node.type === 'shop_premium'">
          <div class="card-field">
            <span>Shop Type:</span>
            <span class="card-field-val">{{ node.data.type }}</span>
          </div>
          
          <!-- Grouped Premium Contents -->
          <div v-if="node.data.items && node.data.items.length > 0" class="card-grouped-section">
            <div class="card-grouped-header">🎁 Содержимое комплекта:</div>
            <div class="card-grouped-items">
              <div v-for="itemId in node.data.items" :key="itemId" class="card-grouped-item">
                <span>{{ getItemEmoji(itemId) }}</span>
                <span class="truncate" style="max-width: 140px;">{{ getItemName(itemId) }}</span>
              </div>
            </div>
          </div>
        </template>

        <template v-else-if="node.type === 'shop_super'">
          <div class="card-field">
            <span>Price:</span>
            <span class="card-field-val">🔵 {{ node.data.price }}</span>
          </div>
          
          <!-- Grouped Super Contents -->
          <div v-if="node.data.items && node.data.items.length > 0" class="card-grouped-section">
            <div class="card-grouped-header">🎁 Содержимое комплекта:</div>
            <div class="card-grouped-items">
              <div v-for="itemId in node.data.items" :key="itemId" class="card-grouped-item">
                <span>{{ getItemEmoji(itemId) }}</span>
                <span class="truncate" style="max-width: 140px;">{{ getItemName(itemId) }}</span>
              </div>
            </div>
          </div>
        </template>

        <template v-else-if="node.type === 'strategy'">
          <div class="card-field" v-if="node.data.heal_threshold_self !== undefined">
            <span>Self Heal:</span>
            <span class="card-field-val">{{ Math.round((node.data.heal_threshold_self || 0) * 100) }}%</span>
          </div>
          <div class="card-field" v-if="node.data.target_weights">
            <span>Weights:</span>
            <span class="card-field-val text-xs">A: {{ node.data.target_weights.aggro }} | HP: {{ node.data.target_weights.hp_percent }}</span>
          </div>
        </template>

        <template v-else-if="node.type === 'settings'">
          <div class="card-field">
            <span>Параметров настроек:</span>
            <span class="card-field-val">{{ Object.keys(node.data).length }} групп</span>
          </div>
        </template>

        <template v-else-if="node.type === 'settings_sub'">
          <div v-if="node.id === 'settings_starter_items' && node.data" class="card-grouped-section w-full">
            <div class="card-grouped-header">🎒 Стартовый инвентарь:</div>
            <div class="card-grouped-items">
              <div v-for="itm in node.data" :key="itm.item_id" class="card-grouped-item">
                <span>{{ getItemEmoji(itm.item_id) }}</span>
                <span class="truncate" style="max-width: 140px;">{{ getItemName(itm.item_id) }} x{{ itm.count }}</span>
              </div>
            </div>
          </div>
          
          <template v-else>
            <div v-if="typeof node.data === 'object' && node.data !== null" class="flex flex-col gap-1 w-full">
              <div v-for="(v, k) in node.data" :key="k" class="card-field w-full">
                <span class="capitalize text-muted text-xs truncate" style="max-width: 120px;" :title="k">{{ k.replace('_', ' ') }}:</span>
                <span class="card-field-val text-xs truncate" style="max-width: 150px;" :title="v">{{ formatValue(v) }}</span>
              </div>
            </div>
            <div class="card-field" v-else>
              <span>Значение:</span>
              <span class="card-field-val truncate" style="max-width: 160px;">{{ node.data }}</span>
            </div>
          </template>
        </template>
      </template>

      <!-- ==================== EDIT MODE VIEW ==================== -->
      <template v-else>
        <!-- ITEM EDITOR FORM -->
        <div v-if="node.type === 'item'" class="flex flex-col gap-3">
          <div class="form-section-title">📦 Редактор Предмета</div>
          
          <div class="flex flex-col gap-1">
            <span class="text-xxs font-bold text-muted">ID Предмета</span>
            <input v-model="localData.id" type="text" :disabled="!node.isNew" required />
          </div>
          
          <div class="flex gap-2">
            <div class="flex flex-col gap-1" style="flex: 1;">
              <span class="text-xxs font-bold text-muted">Эмодзи</span>
              <input v-model="localData.emoji" type="text" required />
            </div>
            <div class="flex flex-col gap-1" style="flex: 2;">
              <span class="text-xxs font-bold text-muted">Ранг</span>
              <select v-model="localData.rank" required>
                <option value="common">Обычный</option>
                <option value="uncommon">Необычный</option>
                <option value="rare">Редкий</option>
                <option value="epic">Эпический</option>
                <option value="mystical">Мистический</option>
                <option value="legendary">Легендарный</option>
                <option value="mythical">Мифический</option>
              </select>
            </div>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-xxs font-bold text-muted">Тип</span>
            <select v-model="localData.type" required>
              <option value="eat">Еда</option>
              <option value="weapon">Оружие</option>
              <option value="armor">Броня</option>
              <option value="backpack">Рюкзак</option>
              <option value="collecting">Инструмент сбора</option>
              <option value="egg">Яйцо</option>
              <option value="case">Сундук</option>
              <option value="recipe">Рецепт</option>
              <option value="rune">Руна</option>
              <option value="material">Материал</option>
              <option value="special">Специальный</option>
              <option value="sleep">Мебель</option>
              <option value="incubation_boost">Буст инкубации</option>
              <option value="training_boost">Буст тренировки</option>
              <option value="dummy">Заглушка</option>
              <option value="book">Книга</option>
            </select>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-xxs font-bold text-muted">Сохранить в файл</span>
            <select v-model="localData.file_name" required>
              <option v-for="file in itemFiles" :key="file" :value="file">{{ file }}</option>
            </select>
          </div>

          <div class="form-section-title">💰 Цены & Торговля</div>
          <div class="flex flex-col gap-2 p-2 rounded bg-zinc-900/60 border border-zinc-800">
            <div class="flex justify-between items-center">
              <span class="text-xs">Скупщик покупает</span>
              <input v-model="localData.buyer" type="checkbox" style="width: auto;" />
            </div>
            <div class="flex justify-between items-center" v-if="localData.buyer">
              <span class="text-xs text-muted">Цена скупщика</span>
              <input v-model.number="localData.buyer_price" type="number" min="0" style="max-width: 80px;" />
            </div>
            <div class="flex justify-between items-center">
              <span class="text-xs text-error">Запретить продажу (cant_sell)</span>
              <input v-model="localData.cant_sell" type="checkbox" style="width: auto;" />
            </div>
          </div>

          <!-- SUB-FORM: EAT -->
          <div v-if="localData.type === 'eat'" class="flex flex-col gap-2 p-2 bg-purple-950/15 border border-purple-500/10 rounded">
            <span class="text-xs font-bold text-primary">🍲 Опции еды</span>
            <div class="flex justify-between items-center">
              <span class="text-xs">Сытость:</span>
              <input v-model.number="localData.act" type="number" style="max-width: 80px;" />
            </div>
            <div class="flex justify-between items-center">
              <span class="text-xs">Потребитель:</span>
              <select v-model="localData.class" style="max-width: 120px;">
                <option value="ALL">Все</option>
                <option value="Carnivore">Хищники</option>
                <option value="Herbivore">Травоядные</option>
                <option value="Flying">Летающие</option>
              </select>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-xs">Напиток?</span>
              <input v-model="localData.drink" type="checkbox" style="width: auto;" />
            </div>
            <!-- buffs -->
            <div class="grid grid-cols-3 gap-1">
              <div class="flex flex-col gap-1">
                <span class="text-xxs">HP</span>
                <input v-model.number="localData.buffs.heal" type="number" />
              </div>
              <div class="flex flex-col gap-1">
                <span class="text-xxs">Mood</span>
                <input v-model.number="localData.buffs.mood" type="number" />
              </div>
              <div class="flex flex-col gap-1">
                <span class="text-xxs">Nrg</span>
                <input v-model.number="localData.buffs.energy" type="number" />
              </div>
            </div>
            <!-- states -->
            <span class="text-xxs font-bold text-muted">Состояния (states):</span>
            <div v-for="(st, sIdx) in localData.states" :key="sIdx" class="flex gap-1 items-center">
              <select v-model="st.char" style="flex: 2; padding: 2px;">
                <option value="heal">HP</option>
                <option value="mood">Mood</option>
                <option value="energy">Energy</option>
              </select>
              <input v-model.number="st.unit" type="number" placeholder="сила" style="flex: 1; padding: 2px;" />
              <input v-model.number="st.time" type="number" placeholder="сек" style="flex: 1.5; padding: 2px;" />
              <button type="button" class="danger" style="padding: 2px 6px;" @click="localData.states.splice(sIdx, 1)">✕</button>
            </div>
            <button type="button" class="secondary text-xxs" @click="localData.states.push({ char: 'heal', unit: 1, time: 30 })">+ Эффект</button>
          </div>

          <!-- SUBFORM: RECIPE -->
          <div v-if="localData.type === 'recipe'" class="flex flex-col gap-2 p-2 bg-teal-950/15 border border-teal-500/10 rounded">
            <span class="text-xs font-bold text-primary">📜 Рецепт</span>
            <div class="flex justify-between items-center">
              <span class="text-xs">Использований:</span>
              <input v-model.number="localData.abilities.uses" type="number" min="1" style="max-width: 60px;" />
            </div>
            <div class="flex justify-between items-center">
              <span class="text-xs">Время крафта (сек):</span>
              <input v-model.number="localData.time_craft" type="number" min="0" style="max-width: 80px;" />
            </div>
            <div class="text-xxs text-primary font-bold">{{ formatTime(localData.time_craft) }}</div>

            <!-- crafter create branches tabs -->
            <span class="text-xxs font-bold text-muted">Создаваемые ветки (create):</span>
            <div class="flex gap-1">
              <input v-model="newBranchName" type="text" placeholder="Имя" style="flex: 2; padding: 2px; font-size: 0.75rem;" />
              <button type="button" class="secondary text-xxs" @click="addCreateBranch">+</button>
            </div>
            <div class="flex gap-1 flex-wrap mt-1">
              <button 
                v-for="branch in Object.keys(localData.create)" 
                :key="branch" 
                type="button" 
                class="filter-chip"
                style="padding: 2px 6px; font-size: 0.65rem;"
                :class="{ active: activeBranchTab === branch }"
                @click="activeBranchTab = branch"
              >
                {{ branch }}
              </button>
            </div>
            <div v-if="activeBranchTab && localData.create[activeBranchTab]" class="p-2 bg-black/30 rounded">
              <div v-for="(itm, iIdx) in localData.create[activeBranchTab]" :key="iIdx" class="flex gap-1 items-center mt-1">
                <button type="button" class="secondary text-xxs" style="flex: 2; text-align: left; padding: 4px;" @click="$emit('pick-item', val => itm.item = val)">
                  {{ itm.item ? getItemName(itm.item) : 'Выбрать...' }}
                </button>
                <input v-model.number="itm.count" type="number" style="flex: 1; max-width: 40px; padding: 2px;" />
                <button type="button" class="danger" style="padding: 2px 6px;" @click="localData.create[activeBranchTab].splice(iIdx, 1)">✕</button>
              </div>
              <button type="button" class="secondary text-xxs mt-1 w-full" @click="localData.create[activeBranchTab].push({ item: '', type: 'create', count: 1 })">+ Предмет</button>
            </div>

            <!-- Recipe materials -->
            <span class="text-xxs font-bold text-muted mt-1">Требуемые материалы (materials):</span>
            <div v-for="(mat, mIdx) in localData.materials" :key="mIdx" class="flex flex-col gap-1 p-1 bg-black/20 rounded">
              <div class="flex gap-1 items-center">
                <button type="button" class="secondary text-xxs" style="flex: 2; text-align: left; padding: 4px;" @click="$emit('pick-item', val => mat.item = val)">
                  {{ mat.item ? getItemName(mat.item) : 'Ресурс...' }}
                </button>
                <input v-model.number="mat.count" type="number" style="flex: 1; max-width: 40px; padding: 2px;" />
                <button type="button" class="danger" style="padding: 2px 6px;" @click="localData.materials.splice(mIdx, 1)">✕</button>
              </div>
            </div>
            <button type="button" class="secondary text-xxs w-full" @click="localData.materials.push({ item: '', type: 'delete', count: 1 })">+ Ресурс</button>
          </div>

          <!-- SUBFORM: EQUIPMENTS -->
          <div v-if="['weapon', 'armor', 'backpack', 'collecting'].includes(localData.type)" class="flex flex-col gap-2 p-2 bg-orange-950/15 border border-orange-500/10 rounded">
            <span class="text-xs font-bold text-primary">🛡️ Снаряжение</span>
            <div class="flex gap-2">
              <div class="flex flex-col gap-1 w-full">
                <span class="text-xxs">Макс прочность</span>
                <input v-model.number="localData.endurance_max" type="number" />
              </div>
            </div>
            <div v-if="localData.type === 'weapon'" class="flex flex-col gap-1">
              <span class="text-xxs">Урон (Damage Range)</span>
              <div class="flex gap-2">
                <input v-model.number="localData.damage.min" type="number" placeholder="Min" />
                <input v-model.number="localData.damage.max" type="number" placeholder="Max" />
              </div>
            </div>
          </div>
          
          <!-- SUBFORM: RUNE -->
          <div v-if="localData.type === 'rune'" class="flex flex-col gap-2 p-2 bg-purple-950/15 border border-purple-500/10 rounded">
            <span class="text-xs font-bold text-primary">🔮 Руна</span>
            <select v-model.number="localData.abilities.rune_type" class="text-xs">
              <option value="1">1 - Уровни</option>
              <option value="2">2 - Множитель</option>
            </select>
            <div v-if="localData.abilities.rune_type === 1">
              <span class="text-xxs">Макс уровень</span>
              <input v-model.number="localData.abilities.max_lvl" type="number" />
            </div>
            <div v-if="localData.abilities.rune_type === 2" class="flex flex-col gap-1">
              <span class="text-xxs">Множитель</span>
              <input v-model.number="localData.abilities.mult_chance" type="number" step="0.5" />
            </div>
          </div>

          <!-- SUBFORM: SPECIAL -->
          <div v-if="localData.type === 'special'" class="flex flex-col gap-2 p-2 bg-purple-950/15 border border-purple-500/10 rounded">
            <span class="text-xs font-bold text-primary">💎 Спец свойства</span>
            <select v-model="localData.class" class="text-xs">
              <option value="premium">Premium</option>
              <option value="background">Background</option>
              <option value="dino_slot">Dino Slot</option>
              <option value="custom_book">Book</option>
            </select>
            <div v-if="['background'].includes(localData.class)">
              <span class="text-xxs">Data ID</span>
              <input v-model.number="localData.abilities.data_id" type="number" />
            </div>
          </div>
        </div>

        <!-- QUEST EDITOR FORM -->
        <div v-else-if="node.type === 'quest'" class="flex flex-col gap-3">
          <div class="form-section-title">📜 Редактор Квеста</div>
          
          <div class="flex flex-col gap-1">
            <span class="text-xxs font-bold text-muted">Тип задания</span>
            <select v-model="localData.type">
              <option value="get">Принести предмет</option>
              <option value="feed">Покормить питомца</option>
              <option value="collecting">Сбор пищи</option>
              <option value="hunting">Охота</option>
            </select>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-xxs font-bold text-muted">Сложность (★ 1-3)</span>
            <div class="flex gap-2">
              <button 
                v-for="c in [1, 2, 3]" 
                :key="c" 
                type="button" 
                class="filter-chip"
                style="padding: 2px 6px;"
                :class="{ active: localData.complexity === c }"
                @click="localData.complexity = c"
              >
                ★ {{ c }}
              </button>
            </div>
          </div>

          <div class="flex flex-col gap-2 p-2 bg-zinc-900/60 rounded border border-zinc-800">
            <span class="text-xxs font-bold text-primary">💰 Награда</span>
            <div class="flex gap-2">
              <input v-model.number="localData.reward.coins.min" type="number" placeholder="Min" />
              <input v-model.number="localData.reward.coins.max" type="number" placeholder="Max" />
            </div>
          </div>

          <!-- required items list -->
          <div v-if="localData.type === 'get'" class="flex flex-col gap-1">
            <span class="text-xxs font-bold text-muted">Требуемые предметы:</span>
            <div v-for="(item, idx) in localData.data.items" :key="idx" class="flex gap-1 items-center">
              <button type="button" class="secondary text-xxs" style="flex: 2; text-align: left; padding: 4px;" @click="$emit('pick-item', val => localData.data.items[idx] = val)">
                {{ localData.data.items[idx] ? getItemName(localData.data.items[idx]) : 'Выбрать...' }}
              </button>
              <button type="button" class="danger" style="padding: 2px 6px;" @click="localData.data.items.splice(idx, 1)">✕</button>
            </div>
            <button type="button" class="secondary text-xxs w-full" @click="localData.data.items.push('')">+ Предмет</button>
          </div>
        </div>

        <!-- MOB EDITOR FORM -->
        <div v-else-if="node.type === 'mob'" class="flex flex-col gap-3">
          <div class="form-section-title">👾 Редактор Моба</div>
          <div class="flex flex-col gap-2 p-2 bg-zinc-900/60 rounded border border-zinc-800">
            <span class="text-xxs font-bold text-primary">Здоровье HP Range</span>
            <div class="flex gap-2">
              <input v-model.number="localData.mobs_default_stats.hp.min" type="number" placeholder="Min" />
              <input v-model.number="localData.mobs_default_stats.hp.max" type="number" placeholder="Max" />
            </div>
          </div>
          <div class="flex flex-col gap-2 p-2 bg-zinc-900/60 rounded border border-zinc-800">
            <span class="text-xxs font-bold text-primary">Урон Damage Range</span>
            <div class="flex gap-2">
              <input v-model.number="localData.mobs_default_stats.damage.min" type="number" placeholder="Min" />
              <input v-model.number="localData.mobs_default_stats.damage.max" type="number" placeholder="Max" />
            </div>
          </div>
          <!-- Loot list -->
          <div class="flex flex-col gap-1">
            <span class="text-xxs font-bold text-muted">Возможный дроп (loot):</span>
            <div v-for="(lootId, idx) in localData.loot" :key="idx" class="flex gap-1 items-center">
              <button type="button" class="secondary text-xxs" style="flex: 2; text-align: left; padding: 4px;" @click="$emit('pick-item', val => localData.loot[idx] = val)">
                {{ localData.loot[idx] ? getItemName(localData.loot[idx]) : 'Выбрать...' }}
              </button>
              <button type="button" class="danger" style="padding: 2px 6px;" @click="localData.loot.splice(idx, 1)">✕</button>
            </div>
            <button type="button" class="secondary text-xxs w-full" @click="localData.loot.push('')">+ Добавить дроп</button>
          </div>
        </div>

        <!-- JOURNEY EDITOR FORM -->
        <div v-else-if="node.type === 'journey'" class="flex flex-col gap-3">
          <div class="form-section-title">🧭 Редактор События</div>
          <div class="flex flex-col gap-1">
            <span class="text-xxs font-bold text-muted">Тип расчета шанса</span>
            <select v-model="localData.chance_config.type">
              <option value="static">Статичный</option>
              <option value="random">Диапазон</option>
            </select>
          </div>
          <div v-if="localData.chance_config.type === 'static'" class="flex flex-col gap-1">
            <span class="text-xxs text-muted">Базовый шанс (0-1)</span>
            <input v-model.number="localData.chance_config.base" type="number" step="0.05" />
          </div>
          <div v-if="localData.chance_config.type === 'random'" class="flex gap-2">
            <input v-model.number="localData.chance_config.min" type="number" step="0.05" placeholder="Min" />
            <input v-model.number="localData.chance_config.max" type="number" step="0.05" placeholder="Max" />
          </div>
        </div>

        <!-- COMBAT STRATEGY FORM -->
        <div v-else-if="node.type === 'strategy'" class="flex flex-col gap-3">
          <div class="form-section-title">⚔️ Тактика Боя</div>
          <div class="flex flex-col gap-1">
            <span class="text-xxs">Агро (aggro): {{ localData.target_weights.aggro }}</span>
            <input v-model.number="localData.target_weights.aggro" type="range" min="-5" max="5" step="0.2" />
          </div>
          <div class="flex flex-col gap-1 mt-1">
            <span class="text-xxs">HP Pct: {{ localData.target_weights.hp_percent }}</span>
            <input v-model.number="localData.target_weights.hp_percent" type="range" min="-5" max="5" step="0.2" />
          </div>
          <div class="flex flex-col gap-1 mt-1">
            <span class="text-xxs">Самолечение: {{ Math.round(localData.heal_threshold_self * 100) }}%</span>
            <input v-model.number="localData.heal_threshold_self" type="range" min="0" max="1" step="0.05" />
          </div>
        </div>

        <!-- SETTINGS SUB FORM -->
        <div v-else-if="node.type === 'settings' || node.type === 'settings_sub'" class="flex flex-col gap-3">
          <div class="form-section-title">⚙️ Настройки</div>
          
          <template v-if="node.id === 'settings_starter_items'">
            <div v-for="(itm, idx) in localData" :key="idx" class="flex gap-1 items-center p-1 bg-black/20 rounded">
              <button type="button" class="secondary text-xxs" style="flex: 2; text-align: left; padding: 4px;" @click="$emit('pick-item', val => localData[idx].item_id = val)">
                {{ localData[idx].item_id ? getItemName(localData[idx].item_id) : 'Выбрать...' }}
              </button>
              <input v-model.number="localData[idx].count" type="number" style="flex: 1; max-width: 40px; padding: 2px;" />
              <button type="button" class="danger" style="padding: 2px 6px;" @click="localData.splice(idx, 1)">✕</button>
            </div>
            <button type="button" class="secondary text-xxs w-full" @click="localData.push({ item_id: '', count: 1, abilities: { interact: false } })">+ Предмет</button>
          </template>
          
          <template v-else>
            <div v-for="(val, key) in localData" :key="key" class="flex flex-col gap-1">
              <span class="text-xxs font-bold text-muted capitalize">{{ key.replace('_', ' ') }}</span>
              <input v-if="typeof val === 'number'" v-model.number="localData[key]" type="number" style="padding: 2px; font-size: 0.75rem;" />
              <input v-else-if="typeof val === 'string'" v-model="localData[key]" type="text" style="padding: 2px; font-size: 0.75rem;" />
              <input v-else-if="typeof val === 'boolean'" v-model="localData[key]" type="checkbox" style="width: auto;" />
              <textarea v-else v-model="serializedParams[key]" rows="3" style="padding: 2px; font-size: 0.7rem;"></textarea>
            </div>
          </template>
        </div>

        <!-- FORM ACTION BUTTONS -->
        <div class="flex gap-2 mt-4 pb-2">
          <button type="button" @click="save" class="font-bold w-full" style="padding: 6px 12px; font-size: 0.8rem;">💾 Сохранить</button>
          <button type="button" class="secondary" @click="$emit('cancel')" style="padding: 6px 12px; font-size: 0.8rem;">Отмена</button>
        </div>
      </template>

    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue';

const props = defineProps({
  node: {
    type: Object,
    required: true
  },
  scale: {
    type: Number,
    required: true
  },
  selected: {
    type: Boolean,
    default: false
  },
  allItems: {
    type: Object,
    required: false,
    default: () => ({})
  },
  localization: {
    type: Object,
    required: false,
    default: () => ({})
  }
});

const emit = defineEmits(['update:position', 'click', 'contextmenu', 'save', 'cancel', 'pick-item']);

const dragging = ref(false);
const startOffset = ref({ x: 0, y: 0 });

const localData = ref({});
const serializedParams = reactive({});
const newBranchName = ref('');
const activeBranchTab = ref('main');

const startDrag = (e) => {
  if (e.button !== 0) return;
  // If clicked inside form inputs, sliders, checkboxes, buttons, tags - do NOT drag!
  if (e.target.closest('input, select, textarea, button, .filter-chip, .card-grouped-item')) {
    return;
  }
  dragging.value = true;
  startOffset.value = {
    x: e.clientX / props.scale - props.node.x,
    y: e.clientY / props.scale - props.node.y
  };
  
  document.addEventListener('mousemove', doDrag);
  document.addEventListener('mouseup', stopDrag);
  e.preventDefault();
};

const doDrag = (e) => {
  if (!dragging.value) return;
  const newX = e.clientX / props.scale - startOffset.value.x;
  const newY = e.clientY / props.scale - startOffset.value.y;
  
  const snap = 8;
  const snappedX = Math.round(newX / snap) * snap;
  const snappedY = Math.round(newY / snap) * snap;
  
  emit('update:position', { x: snappedX, y: snappedY });
};

const stopDrag = () => {
  dragging.value = false;
  document.removeEventListener('mousemove', doDrag);
  document.removeEventListener('mouseup', stopDrag);
};

// Clones payload config node.data into edit mode localData
const initLocalData = () => {
  if (props.node && props.node.data) {
    const copy = JSON.parse(JSON.stringify(props.node.data));
    
    if (props.node.type === 'item') {
      if (!copy.image) copy.image = { background: 'grey_bg', frame: 'elipse', icon: '' };
      if (!copy.groups) copy.groups = [];
      if (!copy.buffs) copy.buffs = { heal: 0, mood: 0, energy: 0 };
      if (!copy.states) copy.states = [];
      if (!copy.create) copy.create = { main: [] };
      if (!copy.materials) copy.materials = [];
      if (!copy.ignore_preview) copy.ignore_preview = [];
      if (!copy.abilities) copy.abilities = {};
      if (!copy.damage) copy.damage = { min: 0, max: 0 };
      if (!copy.drop_items) copy.drop_items = [];
      if (copy.buyer === undefined) copy.buyer = true;
      if (copy.buyer_price === undefined) copy.buyer_price = 0;
      copy.id = props.node.id;
      copy.file_name = props.node.file_name || 'items.json';
      
      const branches = Object.keys(copy.create);
      if (branches.length > 0) {
        activeBranchTab.value = branches[0];
      }
    } else if (props.node.type === 'quest') {
      if (!copy.reward) copy.reward = { coins: { min: 0, max: 0 }, max_items: 0 };
      if (!copy.reward.coins) copy.reward.coins = { min: 0, max: 0 };
      if (!copy.data) copy.data = { items: [], eat_rare: [] };
      if (!copy.data.items) copy.data.items = [];
      if (!copy.data.eat_rare) copy.data.eat_rare = [];
    } else if (props.node.type === 'mob') {
      if (!copy.mobs_default_stats) copy.mobs_default_stats = { hp: { min: 0, max: 0 }, damage: { min: 0, max: 0 } };
      if (!copy.mobs_default_stats.hp) copy.mobs_default_stats.hp = { min: 0, max: 0 };
      if (!copy.mobs_default_stats.damage) copy.mobs_default_stats.damage = { min: 0, max: 0 };
      if (!copy.loot) copy.loot = [];
    } else if (props.node.type === 'journey') {
      if (!copy.chance_config) copy.chance_config = { type: 'static', base: 0.5 };
      if (!copy.outcomes) copy.outcomes = [];
    } else if (props.node.type === 'achievement') {
      if (!copy.award) copy.award = { coins: 0, exp: 0, items: [] };
      if (!copy.award.items) copy.award.items = [];
      if (copy.secret === undefined) copy.secret = false;
    } else if (props.node.type === 'shop_premium') {
      if (!copy.items) copy.items = [];
    } else if (props.node.type === 'shop_super') {
      if (!copy.items) copy.items = [];
    } else if (props.node.type === 'strategy') {
      if (!copy.target_weights) copy.target_weights = { aggro: 0, hp_percent: 0, base_damage: 0 };
      if (copy.heal_threshold_self === undefined) copy.heal_threshold_self = 0.5;
    } else if (props.node.type === 'settings_sub') {
      Object.keys(copy).forEach(k => {
        if (typeof copy[k] === 'object' && copy[k] !== null) {
          serializedParams[k] = JSON.stringify(copy[k], null, 2);
        }
      });
    }
    
    localData.value = copy;
  }
};

watch(() => props.selected, (isSelected) => {
  if (isSelected) {
    initLocalData();
  }
}, { immediate: true });

const itemFiles = [
  'items.json', 'book.json', 'boosters.json', 'case.json', 'collecting_acs.json', 'combat_items.json',
  'dungeon.json', 'eat.json', 'eggs.json', 'game_acs.json', 'heal.json', 'journey_acs.json',
  'materials.json', 'recipes.json', 'runes.json', 'sleep_acs.json', 'special.json'
];

const addCreateBranch = () => {
  const name = newBranchName.value.trim();
  if (name && !localData.value.create[name]) {
    localData.value.create[name] = [];
    activeBranchTab.value = name;
    newBranchName.value = '';
  }
};

const toggleEatRare = (r) => {
  if (!localData.value.data) {
    localData.value.data = {};
  }
  if (!localData.value.data.eat_rare) {
    localData.value.data.eat_rare = [];
  }
  if (!localData.value.data.eat_rare.includes(r)) {
    localData.value.data.eat_rare.push(r);
  }
};

const toggleDummySystemFlag = (checked) => {
  if (checked) {
    localData.value.cant_sell = true;
    localData.value.buyer = false;
  }
};

const save = () => {
  if (props.node.type === 'settings_sub') {
    Object.keys(serializedParams).forEach(k => {
      try {
        localData.value[k] = JSON.parse(serializedParams[k]);
      } catch (e) {
        console.error("Failed to parse settings JSON: ", e);
      }
    });
  }
  
  emit('save', {
    ...props.node,
    id: props.node.type === 'item' ? localData.value.id : props.node.id,
    file_name: props.node.type === 'item' ? localData.value.file_name : props.node.file_name,
    data: localData.value
  });
};

// Formatting helpers
const formatValue = (v) => {
  if (typeof v === 'boolean') return v ? 'Yes ✅' : 'No ❌';
  if (typeof v === 'object' && v !== null) {
    if (Array.isArray(v)) return `[Array of ${v.length}]`;
    return `[Object of ${Object.keys(v).length} keys]`;
  }
  return v;
};

const formatTime = (seconds) => {
  if (!seconds || seconds <= 0) return 'Мгновенно';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  
  let str = '';
  if (hours > 0) str += `${hours} ч. `;
  if (minutes > 0) str += `${minutes} мин. `;
  if (secs > 0 || str === '') str += `${secs} сек.`;
  return str.trim();
};

// Localization and Emoji lookups inside Card
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

const getItemEmoji = (itemId) => {
  for (const file in props.allItems) {
    if (props.allItems[file][itemId]) {
      return props.allItems[file][itemId].emoji || '📦';
    }
  }
  return '📦';
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

// Helpers for visual card representation
const getRarity = (n) => {
  if (n.type === 'item') {
    return n.data.rank || 'common';
  }
  return 'common';
};

const getEmoji = (n) => {
  if (n.emoji) return n.emoji;
  if (n.type === 'item') return n.data.emoji || '📦';
  if (n.type === 'quest') return '📜';
  if (n.type === 'mob') return '👾';
  if (n.type === 'journey') return '🧭';
  if (n.type === 'achievement') return '🏆';
  if (n.type === 'shop_premium') return '🛒';
  if (n.type === 'shop_super') return '🔵';
  if (n.type === 'strategy') return '⚔️';
  if (n.type === 'settings') return '⚙️';
  if (n.type === 'settings_sub') return '⚙️';
  return '📝';
};

const getRarityColor = (rarity) => {
  const colors = {
    common: '#94a3b8',
    uncommon: '#22c55e',
    rare: '#3b82f6',
    epic: '#a855f7',
    mystical: '#ec4899',
    legendary: '#eab308',
    mythical: '#ef4444'
  };
  return colors[rarity] || colors.common;
};

const getTypeColor = (type) => {
  const colors = {
    item: 'rgba(59, 130, 246, 0.25)',
    quest: 'rgba(168, 85, 247, 0.25)',
    mob: 'rgba(239, 68, 68, 0.25)',
    journey: 'rgba(34, 197, 94, 0.25)',
    achievement: 'rgba(234, 179, 8, 0.25)',
    shop_premium: 'rgba(236, 72, 153, 0.25)',
    shop_super: 'rgba(6, 182, 212, 0.25)',
    strategy: 'rgba(249, 115, 22, 0.25)',
    settings: 'rgba(113, 113, 122, 0.25)',
    settings_sub: 'rgba(74, 222, 128, 0.15)'
  };
  return colors[type] || 'rgba(255, 255, 255, 0.1)';
};
</script>

<style scoped>
.edit-mode-content {
  max-height: 380px;
  overflow-y: auto;
  padding-right: 6px;
}

/* Scrollbar styling for edit-mode */
.edit-mode-content::-webkit-scrollbar {
  width: 4px;
}
.edit-mode-content::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
}
.edit-mode-content::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
}
.edit-mode-content::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.35);
}

.form-section-title {
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--md-sys-color-primary);
  margin-top: 10px;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
  padding-bottom: 2px;
}

.text-xxs {
  font-size: 0.65rem;
}
</style>
