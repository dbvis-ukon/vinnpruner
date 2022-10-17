<template lang="pug">
v-container
  v-row
    v-col(cols="4", md="4", lg="3", sm="5", xl="2")
      v-treeview(
        activatable="",
        :open.sync="open",
        :active.sync="active",
        transition="",
        open-on-click="",
        :items="networkTree",
        item-disabled="locked"
      )
    v-divider(vertical="")
    v-col#layerstatrow.d-flex.text-center
      .title.grey--text.text--lighten-1.font-weight-light(v-if="selected == undefined", style="align-self: center")
        | Select a leaf node
      .mx-0.stat-container(v-else="")
        // <WebGLTest2 :networkId="networkId" :mask="mask" v-if="mask != undefined"></WebGLTest2>
        v-card(:key="selected", flat="")
          h4.pb-3 Layer Statistics
          v-row.pb-2(no-gutters="")
            v-col
              h4 Nonzeroes
              span(v-if="layerStats") {{ (layerStats[selected].nonzeroes * 100).toFixed(2) }}%
              span(v-else="") 0%
            v-col
              h4 Pruned
              span(v-if="layerStats") {{ layerStats[selected].total_pruned }}
              span(v-else="") 0
            v-col
              h4 Feature maps

              v-btn(small, height="25px", @click="emitFeatureMap") {{ 'toggle' }}
        LayerStatMosaic(
          :layer-type="this.getMaskedLayerNameForNum(this.selected)"
          :networkId="networkId",
          :mosaics="mosaics",
          :im-width="imWidth",
          :im-height="imHeight",
          :chunk-width="chunkWidth",
          :chunks-per-slice="chunksPerSlice",
          :containerWidth="statWidth",
          :initialBrush="brushSelectionData.find((d) => d.maskedLayerId == selected)",
          @brush-selection-changed="handleBrushSelectionChangeEvent",
          v-if="mosaics.length > 0 && maskLoaded"
        )
        //layer-stat.mx-auto(:network-id='networkId', :mask='mask', v-if='mask != undefined')
        div(v-else)
          v-skeleton-loader(type="image", height="500")

      //
        <div class="mx-auto py-2" v-if="mosaics.length > 0 && maskLoaded">
        <img class="mosaic-piece" v-for="(mosaic, index) in mosaics" :key="index" :src="'data:image/jpeg;base64,' + mosaic" />
        </div>
        <div v-else class="loader">
        <v-progress-circular :size="100" :width="12" color="orange lighten-2" indeterminate></v-progress-circular>
        </div>
      // <LayerStat class="mx-auto" :networkId="networkId" :mask="mask" v-if="mask != undefined" />
</template>

<script>
import LayerStat from "./LayerStat";
import LayerStatMosaic from "./LayerStatMosaic";
import FloatingLayerOutput from "./FloatingLayerOut";

export default {
  components: {
    LayerStat,
    LayerStatMosaic,
    FloatingLayerOutput,
  },
  created() {
    let idx = 0;
    for (let node of this.topologySorted) {
      if (node.name.startsWith("Masked")) {
        this.insertNode(node, this.networkTree[0], 0, idx++);
      }
    }
  },
  data() {
    return {
      networkTree: [{ id: "root", name: "root", children: [] }],
      active: [],
      open: [],
      maskLoaded: false,
      mask: [],
      mosaics: [],
      brushSelectionData: [],
      imHeight: 0,
      imWidth: 0,
      chunkWidth: -1,
      chunksPerSlice: -1,
      statWidth: 1320 - 24,
      layerOutVisible: false,
    };
  },
  methods: {
    handleBrushSelectionChangeEvent(data) {
      data.name = this.getMaskedLayerNameForNum(this.selected);
      data.maskedLayerId = this.selected;
      let idx = this.brushSelectionData.findIndex((d) => d.name == data.name);
      if (idx != -1 && data.remove) {
        this.brushSelectionData.splice(idx, 1);
      } else if (idx != -1) {
        this.brushSelectionData[idx] = data;
      } else {
        this.brushSelectionData.push(data);
      }
      this.$emit("brush-selection-changed", { data: this.brushSelectionData, source: "masks" });
    },
    emitFeatureMap() {
      this.layerOutVisible = !this.layerOutVisible;
      this.$emit("toggle-featuremaps", { selected: this.selected, name: this.getMaskedLayerNameForNum(this.selected) });
    },
    updateFeatureMap() {
      this.$emit("update-featuremaps", { selected: this.selected, name: this.getMaskedLayerNameForNum(this.selected) });
    },
    getMaskedLayerNameForNum(num) {
      let idx = 0;
      for (let layer of this.topologySorted) {
        if (layer.name.includes("Masked")) {
          if (idx++ == num) {
            return layer.name;
          }
        }
      }
      return "UnknownLayer";
    },
    sortLayers(a, b) {
      let idA = parseInt(a.split("-")[1]);
      let idB = parseInt(b.split("-")[1]);
      if (idA < idB) {
        return -1;
      } else if (idA === idB) {
        return 0;
      } else {
        return 1;
      }
    },
    insertNode(toInsert, treeNode, depth, idx) {
      let parents = toInsert.parent_layers.split("/").slice(depth);
      if (treeNode.name == "root") {
        treeNode.name = parents[0];
        treeNode.id = parents[0];
        treeNode.children.push({
          id: idx,
          name: toInsert.name,
        });
        return;
      }
      if (parents.length == 0) {
        return;
      }
      if (treeNode.name == parents[parents.length - 1]) {
        treeNode.children.push({
          id: idx,
          //id: toInsert.name,
          name: toInsert.name,
        });
        treeNode.children.sort((a, b) => this.sortLayers(a.name, b.name));
        return;
      }
      for (let child of treeNode.children) {
        if (parents.includes(child.name)) {
          this.insertNode(toInsert, child, depth + 1, idx);
          return;
        }
      }
      let newParentNode = {
        id: parents[1],
        name: parents[1],
        children: [],
      };
      treeNode.children.push(newParentNode);
      this.insertNode(toInsert, treeNode.children[treeNode.children.length - 1], depth + 1, idx);
    },
    async fetch() {
      this.updateFeatureMap();
      this.maskLoaded = false;
      if (!(this.networkId && this.selected != undefined)) {
        return;
      }
      this.$set(this.networkTree[0], "locked", true);
      let payload = {
        network_id: this.networkId,
        layer_num: this.selected,
        dark: this.theme,
        //requested_width: this.statWidth,
      };
      //console.log(payload);
      let response = await fetch(`${this.apiEndpoint}/layer_stat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify(payload),
      });
      let result = await response.json();
      if (response.status == 200) {
        this.mask = result.mask;
        this.mosaics = result.mosaics;
        this.imsize = result.imsize;
        this.chunkWidth = result.chunk_width;
        this.chunksPerSlice = result.chunks_per_slice;
        this.imWidth = result.img_width;
        this.imHeight = result.img_height;
        this.maskLoaded = true;
      }
      this.$set(this.networkTree[0], "locked", false);
    },
  },
  computed: {
    selected: function () {
      return this.active[this.active.length - 1];
    },
    theme: function () {
      return this.$vuetify.theme.dark;
    },
  },
  props: {
    topologySorted: Array,
    networkId: String,
    apiEndpoint: String,
    layerStats: Array,
  },
  watch: {
    theme: function () {
      this.fetch();
    },
    selected: async function () {
      this.fetch();
    },
  },
};
</script>

<style scoped>
.mosaic-piece {
  width: 100%;
  display: block;
}
.loader {
  min-width: 750px;
}
.stat-container {
  width: 100%;
}
</style>
