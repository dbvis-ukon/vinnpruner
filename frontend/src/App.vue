<template lang="pug">
v-app#global-container
  v-navigation-drawer(app, v-model="settingsOpen", fixed, temporary, right, clipped, width="400", hide-overlay)
    v-list-item.navbar-listitem
      v-list-item-content
        v-list-item-title.title(style="color: black")
          | Settings
        //v-list-item-subtitle
          | set (your) t(h)ings
    v-divider
    dataset-settings(:init-dataset="selectedDataset", :api-url="apiUrl", @image-change="updateDefaultImage")
  v-app-bar.appbar(app, light, color="amber accent-3", dense, flat, clipped-right)
    div ViNNPruner: Visual Neural Network Pruner
    v-spacer
    v-switch.pt-5(v-model="$vuetify.theme.dark", @change="updateThemePreference", inset, color="grey darken-3")
    v-btn.mt-0.ml-1(icon, @click="toggleFollowSystemTheme") 
      v-icon(v-if="followsSystemTheme") mdi-brightness-auto
      v-icon(v-else) mdi-brightness-6
    v-btn.mt-0.ml-1(icon, @click="openSettings") 
      v-icon mdi-cog
  v-main(app)
    v-container#main-container
      // menu bar and charts
      .d-flex.flex-wrap
        v-col(xl="5", lg="5", md="4", sm="6")
          accuracy-chart(:height="200", :chart-data="accChartData", :dark="$vuetify.theme.dark", :key="$vuetify.theme.dark")
        v-col(xl="5", lg="5", md="4", sm="6")
          zeroed-chart(:height="200", :chart-data="lossChartData", :dark="$vuetify.theme.dark", :key="$vuetify.theme.dark")
        v-col.pt-5.pl-4(xl="2", lg="2", md="4", sm="12")
          v-select(
            outlined="",
            dense="",
            :items="networks",
            :item-text="'name'",
            v-model="selectedNetwork",
            :disabled="selectorLabel != 'Go'",
            label="Select a network",
            @change="setSelectedDataset"
          )
          v-select(
            outlined="",
            dense="",
            :items="selectedNetwork ? networks.find((x) => x.name == selectedNetwork).datasets : []",
            v-model="selectedDataset",
            :disabled="selectorLabel != 'Go'",
            label="Select a dataset"
          )
          v-btn.mt-0(
            light,
            depressed="",
            color="orange lighten-2",
            :disabled="!(selectedDataset && selectedNetwork)",
            @click="selectorButtonClick"
          ) {{ selectorLabel }}
      // v-divider.pb-2(horizontal="")
      // displays a list of all network cards in history
      .pt-3
        network-card(
          v-for="network in session.history",
          :key="network.network_id",
          :id="network.network_id",
          :network-id="network.network_id",
          :dataset="network.dataset",
          :dataset-image-num="datasetImageNum",
          :topology="topology",
          :pruner-settings="prunerSettings",
          :stats="networkPruneStats[network.network_id]",
          :iterations="network.it",
          :api-endpoint="apiUrl",
          :evaluation-disabled="false",
          @prunesignal="prune",
          @graphupdate="graphUpdate",
          @removenet="removeNetwork"
        )
      v-dialog(v-model="loading", hide-overlay, persistent, width="400", height="200")
        v-card(color="grey darken-4", dark="")
          v-card-text 
            .pt-3.pb-1 {{ loadingText }} please wait
            v-progress-linear.mb-0(indeterminate, color="orange", height="7")
</template>

<script>
import NetworkCard from "./components/NetworkCard";
import { API_ADDRESS, API_PORT, API_RELATIVE } from "../app.config";
import AccuracyChart from "./components/AccuracyChart";
import ZeroedChart from "./components/ZeroedChart";
import DatasetSettings from "./components/AppSettings/DatasetSettings";

export default {
  name: "App",

  components: {
    NetworkCard,
    AccuracyChart,
    ZeroedChart,
    DatasetSettings,
  },

  mounted() {

    this.mediaEvent = window.matchMedia("(prefers-color-scheme: dark)");
    const theme = localStorage.getItem("darkTheme");
    if (theme === "true") {
      this.$vuetify.theme.dark = true;
    } else if (theme === "system") {
      this.followsSystemTheme = true;
      this.$vuetify.theme.dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      this.mediaEvent.addEventListener("change", this.handleSystemThemeUpdate);
    }
  },

  created() {
    if (API_ADDRESS) {
      this.apiUrl = `${window.location.protocol}//${API_ADDRESS}/:${API_PORT}`;
    } else if (!API_RELATIVE || API_RELATIVE.length == 0) {
      this.apiUrl = `${window.location.protocol}//${window.location.hostname}:${API_PORT}`;
    } else {
      this.apiUrl = `${window.location.protocol}//${window.location.hostname}/${API_RELATIVE}`;     
    }
    window.addEventListener("beforeunload", this.resetSession);
  },

  beforeDestroy() {
    window.removeEventListener("beforeunload", this.resetSession);
    if (this.followsSystemTheme)
      window.matchMedia("(prefers-color-scheme: dark)").removeEventListener("change", this.systemThemeChangeEvent, true);
  },

  computed: {
    lossChartData: function () {
      let sessionHistory = this.session.history ? this.session.history.map((h) => h.it) : [];
      return {
        labels: sessionHistory,
        datasets: [
          {
            label: "Loss",
            borderColor: "#d81b60",
            data: this.lossChartArray,
            fill: false,
          },
        ],
      };
    },
    accChartData: function () {
      let sessionHistory = this.session.history ? this.session.history.map((h) => h.it) : [];
      return {
        labels: sessionHistory,
        datasets: [
          {
            label: "Accuracy",
            borderColor: "#2196f3",
            data: this.accChartArray,
            fill: false,
          },
          {
            label: "Zeroed",
            borderColor: "#66bb6a",
            data: this.zeroChartArray,
            fill: false,
          },
        ],
      };
    },
  },

  methods: {
    handleSystemThemeUpdate(e) {
      console.log(`updating theme based on system preference ${e.matches ? "dark" : "light"}`);
      if (e.matches) {
        this.$vuetify.theme.dark = true;
      } else {
        this.$vuetify.theme.dark = false;
      }
    },
    updateThemePreference() {
      let preference = localStorage.getItem("darkTheme");
      if (preference !== "system") {
        localStorage.setItem("darkTheme", this.$vuetify.theme.dark.toString());
      }
    },
    toggleFollowSystemTheme() {
      let preference = localStorage.getItem("darkTheme");
      if (preference !== "system") {
        this.followsSystemTheme = true;
        this.mediaEvent.addEventListener("change", this.handleSystemThemeUpdate);
        localStorage.setItem("darkTheme", "system");
        this.handleSystemThemeUpdate(window.matchMedia("(prefers-color-scheme: dark)"));
      } else {
        this.followsSystemTheme = false;
        localStorage.setItem("darkTheme", this.$vuetify.theme.dark.toString());
        this.mediaEvent.removeEventListener("change", this.handleSystemThemeUpdate, false);
      }
    },
    updateDefaultImage(data) {
      if (data.dataset == this.selectedDataset) {
        this.datasetImageNum = data.imageNumber;
      }
    },
    openSettings() {
      this.settingsOpen = !this.settingsOpen;
    },
    setSelectedDataset(networkName) {
      this.selectedDataset = this.networks.find((x) => x.name == networkName).datasets[0];
    },
    async removeNetwork(payload) {
      console.log(payload);
      let networkIdx = this.session.history.findIndex((elem) => elem.network_id == payload.network_id);
      console.log(networkIdx);
      let response = await fetch(`${this.apiUrl}/remove`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify(payload),
      });
      let result = await response.json();
      this.$set(this.session, "history", result.history);
      this.$delete(this.networkPruneStats, payload.network_id);
      this.accChartArray.splice(networkIdx, 1);
      this.zeroChartArray.splice(networkIdx, 1);
      this.lossChartArray.splice(networkIdx, 1);
    },
    graphUpdate(payload) {
      this.accChartArray.push(payload.accuracy);
      this.zeroChartArray.push(payload.zeroed);
      this.lossChartArray.push(payload.loss);
    },
    async prune(payload) {
      this.loading = true;
      this.loadingText = `pruning with ${payload.method} for ${payload.iterations} iterations,`;
      if (payload.method == "manual") {
        await this.pruneManual(payload);
      } else {
        await this.pruneWithAlgorithm(payload);
      }
      this.loading = false;
      this.loadingText = "";
    },
    async pruneWithAlgorithm(payload) {
      let webPayload = {
        method: payload.method,
        iterations: payload.iterations,
        pruning_type: payload.type,
        network_id: payload.networkId,
        ratios: payload.ratios,
      };
      //console.log(webPayload);
      let response = await fetch(`${this.apiUrl}/prune`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify(webPayload),
      });
      let result = await response.json();
      // session object refresh
      this.session = result[0];
      this.$set(this.networkPruneStats, result[1].id, {
        global: result[2],
        layers: result[3],
      });
    },
    async pruneManual(payload) {
      let webPayload = {
        method: payload.method,
        custom_masks: payload.customPruningMasks,
        custom_channels: payload.customPruningChannels,
        network_id: payload.networkId,
      };
      console.log(webPayload);
      let response = await fetch(`${this.apiUrl}/prune_manual`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify(webPayload),
      });
      let result = await response.json();
      // session object refresh
      this.session = result[0];
      this.$set(this.networkPruneStats, result[1].id, {
        global: result[2],
        layers: result[3],
      });
    },
    async selectorButtonClick() {
      if (this.selectorLabel == "Go") {
        this.getNetworkSession(this.selectedNetwork, this.selectedDataset);
        this.selectorLabel = "Reset";
      } else {
        this.resetSession();
        this.selectorLabel = "Go";
      }
    },
    async getNetworkSession(network, dataset) {
      this.loading = true;
      this.loadingText = "loading " + network + ",";
      try {
        let payload = {
          network: network,
          dataset: dataset,
        };
        let response = await fetch(`${this.apiUrl}/select_network`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          credentials: "include",
          body: JSON.stringify(payload),
        });
        this.session = await response.json();
        this.loading = false;
        response = await fetch(`${this.apiUrl}/topology`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ network: network }),
        });
        this.topology = await response.json();
        console.log("started new session: " + this.session.session_id);
      } catch (e) {
        console.log(`could not load network ${e}`);
        (this.session = {}), (this.topology = {});
      }
    },
    async resetSession() {
      this.accChartArray = [];
      this.lossChartArray = [];
      this.zeroChartArray = [];
      this.loadingText = "resetting session,";
      this.loading = true;
      (this.session = {}), (this.topology = {});
      await fetch(`${this.apiUrl}/reset`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
      });
      this.loading = false;
      this.loadingText = "";
      console.log("cleared session");
    },
  },

  data: () => ({
    followsSystemTheme: false,
    accChartArray: [],
    lossChartArray: [],
    zeroChartArray: [],
    apiUrl: undefined,
    networks: [
      { name: "mlp", datasets: ["mnist"] },
      { name: "lenet", datasets: ["cifar10"] },
      { name: "alexnet", datasets: ["cifar10"] },
      { name: "conv6", datasets: ["cifar10"] },
      { name: "vgg19", datasets: ["cifar10"] },
      { name: "resnet18", datasets: ["cifar10"] },
    ],
    settingsOpen: false,
    selectorLabel: "Go",
    selectedNetwork: null,
    selectedDataset: null,
    datasetImageNum: 0,
    loading: false,
    debugTrue: true,
    loadingText: "",
    session: {},
    topology: {},
    networkPruneStats: {},
    prunerSettings: {
      pruningTypes: ["iterative", "oneshot"],
      pruningMethods: ["lap", "mp", "manual", "rp"],
    },
    mediaEvent: undefined,
  }),
};
</script>


<style lang="scss"scoped>
#global-container.theme--light {
  background-color: rgb(250, 250, 250);
}
#menu-bar {
  margin: 0 auto;
  //max-width: 1200px;
}
.stretch {
  height: 100%;
}
.v-navigation-drawer {
  will-change: initial;
}
.navbar-listitem {
  background: #ffc400;
}
/*.chart-wrapper {
  max-width: 500px;
}*/
.noselect {
  -webkit-touch-callout: none; /* iOS Safari */
  -webkit-user-select: none; /* Safari */
  -khtml-user-select: none; /* Konqueror HTML */
  -moz-user-select: none; /* Old versions of Firefox */
  -ms-user-select: none; /* Internet Explorer/Edge */
  user-select: none; /* Non-prefixed version, currently
                                  supported by Chrome, Edge, Opera and Firefox */
}
</style>