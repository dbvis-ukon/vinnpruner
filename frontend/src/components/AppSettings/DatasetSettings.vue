<template lang="pug">
v-card.mx-4.mt-4(outlined)
  v-card-title
    v-icon(large) mdi-image-outline
    span.px-2.title.font-weight-light Dataset Default Image
  v-card-text
    v-select(outlined, dense, :items="datasets", v-model="selectedDataset", @change="fetch")
    v-slider(v-model="datasetNumSlider", :max="datasetNumSliderMax", @end="fetch")
      template(v-slot:append)
        v-text-field.pt-0.mt-0(v-model="datasetNumSlider", @change="fetch" single-line, hide-details, style="width: 60px", type="number")
    v-card.mx-auto(v-if="selectedDataset != undefined")
      img.dataset-image(:src="'data:image/jpeg;base64,' + imgdata", v-if="!loading")
      v-row.reference-container.ma-0.pb-1(v-show="loading")
        v-progress-circular.temp-container(indeterminate, size="30", width="5", color="grey lighten-5")
        img.temp-image(:src="placeholder", align="center")
      //v-img(:src="'data:image/jpeg;base64,' + imgdata", :lazy-src="placeholder", :key="imgdata")
        template(v-slot:placeholder)
          v-row.fill-height.ma-0(align="center", justify="center")
            v-progress-circular(indeterminate, color="grey lighten-5")
      v-card-title {{ loading ? 'getting image...' : className[0].toUpperCase() + className.substring(1) }}
</template>

<script>
import tempImg from "@/assets/didier.png";
export default {
  methods: {
    getSettings() {
            let raw = localStorage.dataset;
      if (raw) {
        let settings = JSON.parse(raw);
        if (settings[this.selectedDataset]) this.datasetNumSlider = settings[this.selectedDataset].start;
      }
    },
    async fetch() {
      if (!this.selectedDataset) {
        return;
      }
      if (this.selectedDataset) {
        if (!localStorage.dataset) localStorage.dataset = JSON.stringify({});
        let settings = JSON.parse(localStorage.dataset);
        settings[this.selectedDataset] = { start: this.datasetNumSlider, end: this.datasetNumSlider };
        localStorage.dataset = JSON.stringify(settings);
      }
      this.$emit("image-change", {imageNumber: this.datasetNumSlider, dataset: this.selectedDataset});
      //this.imgdata = undefined;
      this.loading = true;
      let payload = {
        start_idx: this.datasetNumSlider,
        end_idx: this.datasetNumSlider + 1,
        dataset: this.selectedDataset,
      };
      let response = await fetch(`${this.apiUrl}/get_dataset_image`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify(payload),
      });
      if (response.status != 200) {
        console.log("invalid request");
        return;
      }
      let data = await response.json();
      this.imgdata = data[0].img_data;
      this.className = data[0].class;
      this.loading = false;
    },
  },
  data() {
    return {
      placeholder: tempImg,
      loading: true,
      datasets: ["mnist", "cifar10"],
      datasetNumSlider: 0,
      datasetNumSliderMax: 9999,
      selectedDataset: undefined,
      className: undefined,
      imgdata: undefined,
    };
  },
  props: {
    initDataset: String,
    apiUrl: String,
  },
  watch: {
    initDataset: function () {
      this.selectedDataset = this.initDataset;
      this.getSettings();
      this.fetch();
    },
    selectedDataset: function () {
      this.getSettings();
    }
  },
};
</script>

<style lang="scss" scoped>
.dataset-image {
  //image-rendering: crisp-edges;
  width: 100%;
}
.temp-container {
  position: absolute;
  top: calc(50% - 15px);
  left: calc(50% - 15px);
  z-index: 1;
}
.temp-image {
  width: 100%;
}
.reference-container {
  position: relative;
  overflow: hidden;
}
</style>
