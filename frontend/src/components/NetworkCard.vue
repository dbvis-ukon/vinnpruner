<template lang="pug">
v-card.mb-5(:loading="!topologyLoaded", outlined)
  template(slot="progress")
    v-progress-linear(color="orange lighten-2", height="10", indeterminate="")
  // card top view
  v-container.pb-0(v-if="topologyLoaded")
    v-expansion-panels.mb-6(flat="", v-model="panel")
      v-expansion-panel
        v-expansion-panel-header.pl-0.pr-1.py-0(expand-icon="mdi-chevron-down")
          h4 Iteration {{ iterations }} - {{ networkId }}
        v-expansion-panel-content.innerExPan
          NNSVGElement(:containerId="networkId", :netData="nnvisArch", :darkMode="$vuetify.theme.dark", :key="$vuetify.theme.dark")
    v-row(no-gutters="")
      v-col
        h4 Accuracy
        v-progress-circular(color="indigo lighten-2", indeterminate="", size="25", v-if="loadingEvaluation")
        span(v-else="") {{ networkStats.accuracy }}%
      v-col
        h4 Loss
        v-progress-circular(color="indigo lighten-2", indeterminate="", v-if="loadingEvaluation", size="25")
        span(v-else="") {{ networkStats.loss }}
      v-col
        div
          h4 Prune Ratio
          span {{ pruneRatio }}%
      v-col.d-flex
        div
          h4.pl-1 Statistics
          v-progress-circular.ml-1(color="indigo lighten-2", indeterminate="", v-if="loadingEvaluation", size="25")
          //v-dialog(v-else hide-overlay, max-width="1200px", v-model="dialog")
          v-dialog(v-else, hide-overlay, max-width="1200px", v-model="dialog")
            template(v-slot:activator="{ on, attrs }")
              v-btn.px-0(small, height="25px", v-bind="attrs", v-on="on") {{ 'show' }}
            classification-report(@close-dialog="dialog = false", :network-stats="networkStats")
        v-spacer
        .float-right.mt-2
          v-btn(@click="removeNetwork", fab="", dark="", x-small="", color="red")
            v-icon(dark="") mdi-close
  // card bottom view, expansion list and dynamic feature map output
  div(v-if="topologyLoaded")
    FloatingLayerOutput(
      v-if="layerOutVisible",
      :dataset="dataset",
      :layerNum="selectedLayerNum",
      :layerName="selectedLayerName",
      :imageNum="datasetImageNum",
      :apiUrl="apiEndpoint",
      :networkId="networkId",
      :initialSelected="customPruningChannels.find((d) => d.maskedLayerId == selectedLayerNum)",
      :title="`it-${iterations}_${networkId.substring(5, 9)}_${selectedLayerName}`",
      @selected-channels-change="updateManualPruneSettings",
      @window-close="layerOutClose"
    )
    v-list.pb-0
      v-list-group(prepend-icon="mdi-cog")
        template(v-slot:activator="")
          v-list-item-title Pruner Settings
        PrunerSettings(
          :pruningTypes="prunerSettings.pruningTypes",
          :pruningMethods="prunerSettings.pruningMethods",
          :pruningRatios.sync="pruningRatios",
          @prunesignal="prunePassthrough"
        )
    v-list.pt-0
      v-list-group(:disabled="!topologyLoaded", prepend-icon="mdi-layers-search")
        template(v-slot:activator="")
          v-list-item-title Inspect
        NetworkTree(
          :topologySorted="topologySorted",
          :networkId="networkId",
          :apiEndpoint="apiEndpoint",
          :layerStats="stats ? stats.layers : undefined",
          @brush-selection-changed="updateManualPruneSettings",
          @toggle-featuremaps="toggleLayerOut",
          @update-featuremaps="updateLayerOut"
        )
</template>

<script>
import PrunerSettings from "./PrunerSettings";
import NetworkTree from "./NetworkTree";
import NNSVGElement from "./NNSVGElement";
import FloatingLayerOutput from "./FloatingLayerOut";
import ClassificationReport from "./ClassificationReport";

export default {
  watch: {
    topology: function () {
      this.updateRatioList();
    },
  },
  data() {
    return {
      panel: 0,
      dialog: false,
      loadingEvaluation: false,
      networkStats: {},
      topologyLoaded: Object.keys(this.topology).length != 0,
      pruningRatios: [],
      layerOutVisible: false,
      selectedLayerNum: 0,
      selectedLayerName: "",
      selectedFeatureMap: "",
      customPruningMasks: [],
      customPruningChannels: [],
    };
  },
  mounted() {
    if (this.topologyLoaded) {
      this.updateRatioList()
    }
    this.$vuetify.goTo(`#${this.networkId}`, { duration: 500, offset: 0, easing: "easeInOutCubic" });
    this.evaluateNetwork();
  },
  components: {
    PrunerSettings,
    NetworkTree,
    NNSVGElement,
    FloatingLayerOutput,
    ClassificationReport,
  },
  props: {
    topology: Object,
    datasetImageNum: Number,
    prunerSettings: Object,
    apiEndpoint: String,
    networkId: String,
    dataset: String,
    stats: Object,
    iterations: Number,
    evaluationDisabled: Boolean,
  },
  methods: {
    updateRatioList() {
      if (this.topology != {}) {
        this.topologyLoaded = true;
        let pruneTopology = this.topologySorted.filter((m) => m.name.includes("Masked")).length;
        this.pruningRatios = Array(pruneTopology).fill(30);
      } else {
        this.pruningRatios = Array(1).fill(30);
      }
    },
    updateManualPruneSettings(event) {
      if (event.source == "channels") {
        let idx = this.customPruningChannels.findIndex((d) => d.maskedLayerId == event.data.maskedLayerId);
        if (idx != -1 && event.data.channels.length == 0) {
          this.customPruningChannels.splice(idx, 1);
        } else if (idx != -1) {
          this.customPruningChannels[idx] = event.data;
        } else {
          this.customPruningChannels.push(event.data);
        }
      } else if (event.source == "masks") {
        this.customPruningMasks = event.data;
      }
    },
    rand(min, max) {
      return Math.random() * (max - min) + min;
    },
    toggleLayerOut(data) {
      this.updateLayerOut(data);
      this.layerOutVisible = !this.layerOutVisible;
    },
    updateLayerOut(data) {
      this.selectedLayerNum = data.selected;
      this.selectedLayerName = data.name;
    },
    layerOutClose(name) {
      this.layerOutVisible = false;
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
    prunePassthrough(payload) {
      payload.networkId = this.networkId;
      payload.customPruningMasks = this.customPruningMasks;
      payload.customPruningChannels = this.customPruningChannels;
      this.$emit("prunesignal", payload);
    },
    removeNetwork() {
      this.$emit("removenet", { network_id: this.networkId });
    },
    async evaluateNetwork() {
      let startDate = new Date();
      if (this.evaluationDisabled) {
        return;
      }
      this.loadingEvaluation = true;
      let payload = {
        network_id: this.networkId,
        dataset: this.dataset,
      };
      let response = await fetch(`${this.apiEndpoint}/evaluate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify(payload),
      });
      let result = await response.json();
      this.$set(this.networkStats, "accuracy", parseFloat(result.current_acc.toFixed(2)));
      this.$set(this.networkStats, "loss", parseFloat(result.current_loss.toFixed(3)));
      this.$set(this.networkStats, "precisionScores", result.precision_scores);
      this.$set(this.networkStats, "recallScores", result.recall_scores);
      this.$set(this.networkStats, "confusionMatrix", result.confusion_matrix);
      this.$set(this.networkStats, "support", result.support);
      this.$set(this.networkStats, "idxToClass", result.idx_to_class);
      this.$set(this.networkStats, "classPrecisionRecallCurves", result.class_precision_recall_curves);
      this.loadingEvaluation = false;
      let endDate = new Date();
      let seconds = Math.round((endDate.getTime() - startDate.getTime()) / 1000);
      console.log(`evaluation for ${this.networkId} complete after ${seconds} seconds`);
      payload = {
        accuracy: this.networkStats.accuracy,
        loss: this.networkStats.loss,
        zeroed: this.pruneRatio,
      };
      this.$emit("graphupdate", payload);
    },
  },
  computed: {
    topologySorted: function () {
      let ls = [];
      for (let elem in this.topology) {
        ls.push(elem);
      }
      ls.sort((a, b) => this.sortLayers(a, b));
      let top_sorted = [];
      for (let objName of ls) {
        let obj = this.topology[objName];
        obj.name = objName;
        top_sorted.push(obj);
      }
      return top_sorted;
    },
    pruneRatio: function () {
      if (this.stats && this.stats.global.sparsity != -1) {
        return ((1 - this.stats.global.sparsity) * 100).toFixed(2);
      } else {
        return 0;
      }
    },
    nnvisArch: function () {
      const visData = {
        convLayers: [],
        linearLayers: [],
      };

      // add input dimensions as layer
      if (this.topologySorted[0].input_shape[0].length < 3) {
        visData.convLayers.push({
          width: this.topologySorted[0].input_shape[0][0],
          height: this.topologySorted[0].input_shape[0][1],
          depth: 1,
          filterWidth: this.topologySorted[0].kernel_size ? this.topologySorted[0].kernel_size[0] : 0,
          filterHeight: this.topologySorted[0].kernel_size ? this.topologySorted[0].kernel_size[1] : 0,
          rel_x: this.rand(-0.4, 0.4),
          rel_y: this.rand(-0.4, 0.4),
        });
      } else {
        visData.convLayers.push({
          width: this.topologySorted[0].input_shape[0][3],
          height: this.topologySorted[0].input_shape[0][2],
          depth: this.topologySorted[0].input_shape[0][1],
          filterWidth: this.topologySorted[0].kernel_size ? this.topologySorted[0].kernel_size[0] : 0,
          filterHeight: this.topologySorted[0].kernel_size ? this.topologySorted[0].kernel_size[1] : 0,
          rel_x: this.rand(-0.4, 0.4),
          rel_y: this.rand(-0.4, 0.4),
        });
      }

      // render behavior when pruning was applied
      if (this.stats) {
        let prunedLayer = this.stats.layers[0];
        let lastLayer = prunedLayer;
        for (let i = 0; i < this.stats.layers.length - 1; i++) {
          lastLayer = prunedLayer.name.includes("MaskedConv") ? prunedLayer : lastLayer;
          prunedLayer = this.stats.layers[i];
          if (prunedLayer && prunedLayer.name.includes("MaskedConv")) {
            let width = Math.round(prunedLayer.output_shape[2] * prunedLayer.nonzeroes);
            let height = Math.round(prunedLayer.output_shape[3] * prunedLayer.nonzeroes);
            let depth = Math.round(prunedLayer.output_shape[1] * prunedLayer.nonzeroes);
            if (width == 0) {
              width = 1;
            }
            if (height == 0) {
              height = 1;
            }
            if (depth == 0) {
              depth = 1;
            }
            visData.convLayers.push({
              width: width,
              height: height,
              depth: depth,
              filterWidth: lastLayer.kernel_size[0],
              filterHeight: lastLayer.kernel_size[1],
              rel_x: this.rand(-0.4, 0.4),
              rel_y: this.rand(-0.4, 0.4),
            });
          } else if (prunedLayer && (prunedLayer.name.includes("MaskedLinear") || prunedLayer.name.includes("linear"))) {
            let size = Math.round(prunedLayer.output_shape[1] * prunedLayer.nonzeroes);
            if (size == 0) {
              size = 1;
            }
            visData.linearLayers.push(size);
          }
        }
        // default behavior
      } else {
        let layer = this.topologySorted[0];
        let lastLayer = layer;
        for (let i = 0; i < this.topologySorted.length - 1; i++) {
          lastLayer = layer.name.includes("MaskedConv") ? layer : lastLayer;
          layer = this.topologySorted[i];
          if (layer.name.includes("MaskedConv")) {
            visData.convLayers.push({
              width: layer.output_shape[0][2],
              height: layer.output_shape[0][3],
              depth: layer.output_shape[0][1],
              filterWidth: lastLayer.kernel_size[0],
              filterHeight: lastLayer.kernel_size[1],
              rel_x: this.rand(-0.4, 0.4),
              rel_y: this.rand(-0.4, 0.4),
            });
          } else if (layer.name.includes("MaskedLinear")) {
            visData.linearLayers.push(layer.output_shape[0][1]);
          }
        }
      }
      visData.linearLayers.push(this.topologySorted[this.topologySorted.length - 1].output_shape[0][1]);
      return visData;
    },
  },
};
</script>

<style lang="scss">
.innerExPan > * {
  padding-top: 0px;
  padding-right: 0px;
  padding-bottom: 0px;
  padding-left: 0px;
}
</style>
