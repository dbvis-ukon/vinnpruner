<template lang="pug">
v-container
  v-row.pt-4
    v-select.mx-3(:items="pruningMethods", label="Pruning Method", v-model="selectedMethod", @change="checkFields", outlined="", dense="")
    v-text-field.mx-3(label="Iterations", v-model.number="iterations", outlined, dense, :disabled="manualMode")
    v-select.mx-3(:items="pruningTypes", label="Pruning Type", v-model="selectedType", outlined, dense, :disabled="manualMode")
    v-btn.mx-3.mt-0(height="40", depressed, @click="pruneSignal", color="primary") Apply
  v-row
    v-col.pt-0
      v-checkbox(v-model="customRatios", label="Custom Pruning Ratios")
      div(v-if="customRatios")
        v-radio-group(v-model="advanced")
          v-row
            v-col.pt-0
              v-radio.radio-padding(label="Quick", :value="false")
              // create list with layers
              .d-flex(v-for="(ratio, index) in pruningRatios", :key="'ratio_' + index")
                v-row
                  v-col(md="3")
                    v-subheader.pb-2 Layer {{ index }}
                  v-col(md="9")
                    v-text-field(:disabled="advanced", v-model.number="pruningRatios[index]", dense="", outlined="", suffix="%") 
            v-col
              v-radio(label="Advanced", :value="true")
              v-textarea(
                :disabled="!advanced",
                v-model="ratioText",
                :rules="[() => layerCountInvalid || 'Entered string does not match layer count']"
              )
              v-btn.mt-2(@click="handleLayerUpdateButton", color="primary", depressed="", :disabled="!layerCountInvalid") Update
</template>

<script>
export default {
  mounted() {
    this.pruningRatiosInternal = this.pruningRatios;
  },
  computed: {
    ratioText: {
      get: function () {
        return this.pruningRatios.join(", ");
      },
      set: function (textInput) {
        return this.parseLayerText(textInput);
      },
    },
  },
  data() {
    return {
      selectedMethod: this.pruningMethods[0],
      selectedType: this.pruningTypes[0],
      customRatios: false,
      advanced: false,
      layerCountInvalid: true,
      pruningRatiosInternal: [],
      iterations: 1,
      manualMode: false,
    };
  },
  props: {
    pruningTypes: Array,
    pruningMethods: Array,
    pruningRatios: Array,
  },
  methods: {
    checkFields(event) {
      if (event == "manual") {
        this.manualMode = true;
      } else {
        this.manualMode = false;
      }
    },
    parseLayerText(textInput) {
      let split = textInput.split(",");
      split.forEach((elem, index, ary) => {
        let newElem = parseInt(elem.trim().replace(/\D/g, ""), 10);
        if (isNaN(newElem)) {
          ary[index] = 0;
        } else {
          ary[index] = newElem;
        }
      });
      if (split.length == this.pruningRatios.length) {
        this.layerCountInvalid = true;
      } else {
        this.layerCountInvalid = false;
      }
      //this.$emit("update:pruningRatios", split);
      this.pruningRatiosInternal = split;
    },
    pruneSignal() {
      let ratioPayload = [];
      if (this.customRatios) {
        ratioPayload = this.pruningRatios.map((r) => r / 100);
      }
      let payload = {
        ratios: ratioPayload,
        iterations: this.iterations,
        method: this.selectedMethod,
        type: this.selectedType,
      };
      this.$emit("prunesignal", payload);
    },
    handleLayerUpdateButton() {
      console.log(this.ratioText);
      this.$emit("update:pruningRatios", this.pruningRatiosInternal);
    },
  },
};
</script>

<style lang="scss" scoped>
.radio-padding {
  padding-bottom: 1rem;
}
</style>