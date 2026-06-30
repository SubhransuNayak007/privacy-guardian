import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type ToolType = 'select' | 'rectangle' | 'rounded-rectangle' | 'circle' | 'brush' | 'polygon';
export type BlurType = 'gaussian' | 'pixelate' | 'black' | 'white' | 'color' | 'mosaic' | 'transparent' | 'motion' | 'context';

export interface EditorLayer {
  id: string;
  name: string;
  type: 'rect' | 'circle' | 'polygon' | 'brush';
  x: number;
  y: number;
  width?: number;
  height?: number;
  radius?: number;
  cornerRadius?: number;
  rotation?: number;
  points?: number[]; // For brush/polygon (x, y alternating array)
  polygon?: number[]; // Flat array of [x, y, x, y...] relative coordinates (0-100) from backend
  
  // Appearance
  blurType: BlurType;
  blurStrength: number; // 0-100
  brushSize?: number; // Size for brush strokes
  color?: string; // If BlurType is color
  opacity: number; // 0-1
  
  // State
  visible: boolean;
  locked: boolean;
}

export type LayerUpdate = { id: string; prev: Partial<EditorLayer>; next: Partial<EditorLayer> };

export type EditorCommand = 
  | { type: 'ADD_LAYERS'; layers: EditorLayer[] }
  | { type: 'DELETE_LAYERS'; layers: EditorLayer[]; indices: number[] }
  | { type: 'UPDATE_LAYERS'; updates: LayerUpdate[] }
  | { type: 'REORDER_LAYER'; id: string; prevIndex: number; nextIndex: number };

interface EditorState {
  // Canvas View State
  zoom: number;
  pan: { x: number; y: number };
  
  // Tools
  currentTool: ToolType;
  
  // Global blur defaults (applied to every new shape drawn)
  defaultBlurType: BlurType;
  defaultBlurStrength: number;
  defaultBrushSize: number;
  defaultColor: string;
  setDefaultBlur: (opts: {
    blurType?: BlurType;
    blurStrength?: number;
    brushSize?: number;
    color?: string;
  }) => void;
  
  // Layers
  layers: EditorLayer[];
  selectedLayerIds: string[];
  
  // Command History
  history: EditorCommand[];
  historyStep: number;
  
  // Actions
  setZoom: (zoom: number) => void;
  setPan: (pan: { x: number; y: number }) => void;
  setTool: (tool: ToolType) => void;
  
  // Initial setup (from AI detection)
  setInitialLayers: (layers: EditorLayer[]) => void;
  
  // History commands
  pushCommand: (cmd: EditorCommand) => void;
  undo: () => void;
  redo: () => void;
  
  // Layer modifications
  addLayer: (layer: Omit<EditorLayer, 'id' | 'name'>) => void;
  
  // Draft vs Commit: updateLayer updates state instantly (for sliders/dragging).
  // commitLayerUpdate pushes the discrete change to history when interaction ends.
  updateLayer: (id: string, updates: Partial<EditorLayer>) => void;
  commitLayerUpdate: (id: string, prev: Partial<EditorLayer>, next: Partial<EditorLayer>) => void;
  
  deleteLayers: (ids: string[]) => void;
  duplicateLayers: (ids: string[]) => void;
  reorderLayer: (id: string, newIndex: number) => void;
  bringForward: (id: string) => void;
  sendBackward: (id: string) => void;
  
  // Original Comparison
  showOriginal: boolean;
  setShowOriginal: (show: boolean) => void;

  isCompareMode: boolean;
  setIsCompareMode: (mode: boolean) => void;
  compareSliderPos: number;
  setCompareSliderPos: (pos: number) => void;

  setSelectedLayers: (ids: string[]) => void;
  clearSelection: () => void;

  // Face Whitelisting
  trustedFaceImages: string[];
  setTrustedFaceImages: (b64s: string[]) => void;
}

export const useEditorStore = create<EditorState>()(
  persist(
    (set, get) => ({
  zoom: 1,
  pan: { x: 0, y: 0 },
  currentTool: 'select',
  layers: [],
  selectedLayerIds: [],
  
  // Blur defaults
  defaultBlurType: 'gaussian',
  defaultBlurStrength: 30,
  defaultBrushSize: 30,
  defaultColor: '#000000',
  setDefaultBlur: (opts) => set((s) => ({
    defaultBlurType:     opts.blurType     ?? s.defaultBlurType,
    defaultBlurStrength: opts.blurStrength ?? s.defaultBlurStrength,
    defaultBrushSize:    opts.brushSize    ?? s.defaultBrushSize,
    defaultColor:        opts.color        ?? s.defaultColor,
  })),
  
  history: [],
  historyStep: -1,
  
  showOriginal: false,
  setShowOriginal: (show) => set({ showOriginal: show }),

  isCompareMode: false,
  setIsCompareMode: (mode) => set({ isCompareMode: mode }),
  compareSliderPos: 0.5,
  setCompareSliderPos: (pos) => set({ compareSliderPos: pos }),

  trustedFaceImages: [],

  setZoom: (zoom) => set({ zoom }),
  setPan: (pan) => set({ pan }),
  setTrustedFaceImages: (b64s) => set({ trustedFaceImages: b64s }),
  setTool: (tool) => set({ currentTool: tool, selectedLayerIds: [] }),

  setInitialLayers: (layers) => set({
    layers,
    history: [],
    historyStep: -1,
    selectedLayerIds: []
  }),

  pushCommand: (cmd) => set((state) => {
    const newHistory = state.history.slice(0, state.historyStep + 1);
    newHistory.push(cmd);
    return {
      history: newHistory,
      historyStep: newHistory.length - 1
    };
  }),

  undo: () => set((state) => {
    if (state.historyStep < 0) return state;
    
    const cmd = state.history[state.historyStep];
    let newLayers = [...state.layers];

    if (cmd.type === 'ADD_LAYERS') {
      const addedIds = cmd.layers.map(l => l.id);
      newLayers = newLayers.filter(l => !addedIds.includes(l.id));
    } else if (cmd.type === 'DELETE_LAYERS') {
      // Restore deleted layers at their exact indices
      const sortedRestore = cmd.layers.map((l, i) => ({ layer: l, index: cmd.indices[i] }))
                                      .sort((a, b) => a.index - b.index);
      sortedRestore.forEach(({ layer, index }) => {
        newLayers.splice(index, 0, layer);
      });
    } else if (cmd.type === 'UPDATE_LAYERS') {
      cmd.updates.forEach(u => {
        const i = newLayers.findIndex(l => l.id === u.id);
        if (i !== -1) newLayers[i] = { ...newLayers[i], ...u.prev };
      });
    } else if (cmd.type === 'REORDER_LAYER') {
      const i = newLayers.findIndex(l => l.id === cmd.id);
      if (i !== -1) {
        const [moved] = newLayers.splice(i, 1);
        newLayers.splice(cmd.prevIndex, 0, moved);
      }
    }

    return {
      layers: newLayers,
      historyStep: state.historyStep - 1,
      selectedLayerIds: []
    };
  }),

  redo: () => set((state) => {
    if (state.historyStep >= state.history.length - 1) return state;
    
    const nextStep = state.historyStep + 1;
    const cmd = state.history[nextStep];
    let newLayers = [...state.layers];

    if (cmd.type === 'ADD_LAYERS') {
      newLayers = [...cmd.layers, ...newLayers]; // inserted at beginning (top of stack)
    } else if (cmd.type === 'DELETE_LAYERS') {
      const deletedIds = cmd.layers.map(l => l.id);
      newLayers = newLayers.filter(l => !deletedIds.includes(l.id));
    } else if (cmd.type === 'UPDATE_LAYERS') {
      cmd.updates.forEach(u => {
        const i = newLayers.findIndex(l => l.id === u.id);
        if (i !== -1) newLayers[i] = { ...newLayers[i], ...u.next };
      });
    } else if (cmd.type === 'REORDER_LAYER') {
      const i = newLayers.findIndex(l => l.id === cmd.id);
      if (i !== -1) {
        const [moved] = newLayers.splice(i, 1);
        newLayers.splice(cmd.nextIndex, 0, moved);
      }
    }

    return {
      layers: newLayers,
      historyStep: nextStep,
      selectedLayerIds: []
    };
  }),

  addLayer: (layer) => {
    const id = crypto.randomUUID();
    const state = get();
    const newLayer: EditorLayer = {
      ...layer,
      id,
      name: `Layer ${state.layers.length + 1}`
    };
    
    set({
      layers: [newLayer, ...state.layers],
      selectedLayerIds: [id],
      currentTool: 'select'
    });
    
    get().pushCommand({
      type: 'ADD_LAYERS',
      layers: [newLayer]
    });
  },

  updateLayer: (id, updates) => set((state) => ({
    layers: state.layers.map((l) => (l.id === id ? { ...l, ...updates } : l))
  })),

  commitLayerUpdate: (id, prev, next) => {
    get().pushCommand({
      type: 'UPDATE_LAYERS',
      updates: [{ id, prev, next }]
    });
  },

  deleteLayers: (ids) => {
    const state = get();
    const deletedLayers: EditorLayer[] = [];
    const deletedIndices: number[] = [];
    
    const newLayers = state.layers.filter((l, i) => {
      if (ids.includes(l.id)) {
        deletedLayers.push(l);
        deletedIndices.push(i);
        return false;
      }
      return true;
    });
    
    set({
      layers: newLayers,
      selectedLayerIds: state.selectedLayerIds.filter((id) => !ids.includes(id))
    });
    
    get().pushCommand({
      type: 'DELETE_LAYERS',
      layers: deletedLayers,
      indices: deletedIndices
    });
  },

  duplicateLayers: (ids) => {
    const state = get();
    const layersToDuplicate = state.layers.filter(l => ids.includes(l.id));
    const duplicated = layersToDuplicate.map(l => ({
      ...l,
      id: crypto.randomUUID(),
      name: `${l.name} Copy`,
      x: l.x + 20,
      y: l.y + 20
    }));
    
    set({
      layers: [...duplicated, ...state.layers],
      selectedLayerIds: duplicated.map(l => l.id)
    });
    
    get().pushCommand({
      type: 'ADD_LAYERS',
      layers: duplicated
    });
  },

  reorderLayer: (id, newIndex) => {
    const state = get();
    const oldIndex = state.layers.findIndex(l => l.id === id);
    if (oldIndex === -1 || oldIndex === newIndex) return;
    
    const newLayers = [...state.layers];
    const [moved] = newLayers.splice(oldIndex, 1);
    newLayers.splice(newIndex, 0, moved);
    
    set({ layers: newLayers });
    get().pushCommand({
      type: 'REORDER_LAYER',
      id,
      prevIndex: oldIndex,
      nextIndex: newIndex
    });
  },

  bringForward: (id) => {
    const state = get();
    const idx = state.layers.findIndex(l => l.id === id);
    if (idx > 0) get().reorderLayer(id, idx - 1);
  },

  sendBackward: (id) => {
    const state = get();
    const idx = state.layers.findIndex(l => l.id === id);
    if (idx < state.layers.length - 1) get().reorderLayer(id, idx + 1);
  },

  setSelectedLayers: (ids) => set({ selectedLayerIds: ids }),
  clearSelection: () => set({ selectedLayerIds: [] })
}),
    {
      name: 'privacy-guardian-editor',
      partialize: (state) => ({
        trustedFaceImages: state.trustedFaceImages,
        defaultBlurType: state.defaultBlurType,
        defaultBlurStrength: state.defaultBlurStrength,
        defaultBrushSize: state.defaultBrushSize,
        defaultColor: state.defaultColor,
      }),
    }
  )
);
