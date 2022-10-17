<template>
  <div class="canvas-container" :id="'graph' + containerId"></div>
</template>

<script>
export default {
  props: {
    containerId: String,
    netData: Object,
    darkMode: Boolean
  },
  mounted() {
    // let architecture = [{width: 20, height: 40, depth: 40, stride: 11}]
    // let architecture2 = [700, 16];
    let architecture = this.netData.convLayers;
    let architecture2 = this.netData.linearLayers;
    let alexnet = window.AlexNet("graph" + this.containerId, this.darkMode);
    alexnet.redraw({
      architecture_: architecture,
      architecture2_: architecture2,
      depthScale_: 10,
      logDepth_: true,
      widthScale_: 10,
      logWidth_: true,
      showDims_: true,
      showConvDims_: true,
    });
  },
};
</script>

<style lang="scss">
.canvas-container {
  //border-radius: 5px;
  //background-color: #ffffff;
  border: 0px solid #aaa;
  overflow: hidden;
}
</style>