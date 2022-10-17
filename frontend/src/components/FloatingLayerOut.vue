<template lang="pug">
.draggable-container(ref="draggableContainer", style="top: 50%; left: 50vw")
  v-card.wrapper-container(
    :color="$vuetify.theme.dark ? '' : 'grey lighten-5'",
    :loading="false",
    :class="[constrainHeight ? 'wrapper-constrain-height' : '', unlockPressed ? 'unlocked-height' : '']"
  )
    //template(slot="progress")
      v-progress-linear(color="deep-purple", height="10", indeterminate)
    v-system-bar.draggable-header(height="36", color="orange", @mousedown="dragMouseDown", light)
      v-icon mdi-image-multiple-outline
      span {{ title }}
      v-spacer
      v-btn(icon, small)
        v-icon.pl-2(@click="unlockHeight") {{ constrainHeight ? 'mdi-arrow-split-horizontal' : 'mdi-lock' }}
      v-btn(icon, small)
        v-icon.pl-2(@click="$emit('window-close', title)") mdi-close
    v-slide-y-reverse-transition
      v-btn.mb-7.btn-fix(
        @click="updateMode",
        v-if="selectedChannels.length > 0",
        small,
        absolute,
        fab,
        dark,
        bottom,
        right,
        depressed,
        :color="pruneMode ? 'deep-orange darken-2' : 'light-blue darken-2'"
      ) 
        v-icon(v-if="pruneMode") mdi-image-off-outline
        v-icon(v-else) mdi-image-outline
    .noselect.px-1.pt-2.pb-1(v-if="!loading", :class="[unlockPressed ? 'inner-content-max-height' : 'inner-content']")
      .img-wrapper(v-for="(data, index) in images", :class="[mode == 'conv2d' ? 'px-1' : '']")
        img(
          :key="index",
          :src="data",
          @click="toggleSelect(index)",
          :class="[mode == 'conv2d' ? 'feature-map-conv2d' : 'feature-map-linear', isSelected(index) ? 'img-feature-selected' : 'img-feature']"
        )
    v-container.fill-height(v-else)
      v-row(align="center", justify="center")
        //v-skeleton-loader.ma-4(type="image", height="200px")
        v-avatar.ma-4.metronome-animation(color="indigo lighten-2", size="100")
</template>

<script>
export default {
  mounted() {
    this.fetch();
  },
  watch: {
    layerNum: function () {
      this.fetch();
    },
    imageNum: function () {
      this.fetch();
    },
  },
  props: {
    title: String,
    networkId: String,
    layerName: String,
    layerNum: Number,
    dataset: String,
    imageNum: Number,
    apiUrl: String,
    initialSelected: Object,
  },
  data: function () {
    return {
      positions: {
        clientX: undefined,
        clientY: undefined,
        movementX: 0,
        movementY: 0,
      },
      selectedChannels: [],
      featureMaps: {},
      loading: true,
      constrainHeight: true,
      needsResize: false,
      unlockPressed: false,
      images: [],
      mode: "",
      lock: false,
      pruneMode: true,
    };
  },
  methods: {
    toggleSelect(index) {
      let found = this.selectedChannels.indexOf(index);
      if (found != -1) {
        this.selectedChannels.splice(found, 1);
      } else {
        this.selectedChannels.push(index);
      }
      this.fireUpdateEvent();
    },
    updateMode() {
      this.pruneMode = !this.pruneMode;
      this.fireUpdateEvent();
    },
    fireUpdateEvent() {
      this.$emit("selected-channels-change", {
        data: { name: this.layerName, maskedLayerId: this.layerNum, channels: this.selectedChannels, prune: this.pruneMode },
        source: "channels",
      });
    },
    isSelected(index) {
      const selected = this.selectedChannels.includes(index);
      return selected;
    },
    unlockHeight() {
      this.constrainHeight = !this.constrainHeight;
      this.unlockPressed = true;
    },
    imager() {
      let canvas = document.createElement("canvas");
      let ctx = canvas.getContext("2d");
      let imgdata;
      if (this.title.toLowerCase().includes("conv2d")) {
        this.mode = "conv2d";
        imgdata = ctx.getImageData(0, 0, this.featureMaps.shape[2], this.featureMaps.shape[3]);
        canvas.width = this.featureMaps.shape[2];
        canvas.height = this.featureMaps.shape[3];
        for (let channel of this.featureMaps.output[0]) {
          let i = 0;
          for (let row of channel) {
            for (let pixel of row) {
              imgdata.data[i] = pixel;
              imgdata.data[i + 1] = pixel;
              imgdata.data[i + 2] = pixel;
              imgdata.data[i + 3] = 255;
              i += 4;
            }
          }
          ctx.putImageData(imgdata, 0, 0);
          this.images.push(canvas.toDataURL());
        }
      } else if (this.title.toLowerCase().includes("linear")) {
        this.mode = "linear";
        imgdata = ctx.getImageData(0, 0, 1, 1);
        canvas.width = 1;
        canvas.height = 1;
        let i = 0;
        for (let pixel of this.featureMaps.output[0]) {
          imgdata.data[i] = pixel;
          imgdata.data[i + 1] = pixel;
          imgdata.data[i + 2] = pixel;
          imgdata.data[i + 3] = 255;
          //i += 4;
          ctx.putImageData(imgdata, 0, 0);
          this.images.push(canvas.toDataURL());
        }
      }
    },
    async fetch() {
      if (this.initialSelected) {
        this.pruneMode = this.initialSelected.prune;
        this.selectedChannels = this.initialSelected.channels;
      } else {
        this.selectedChannels = [];
      }
      this.images = [];
      this.loading = true;
      let payload = {
        network_id: this.networkId,
        layer_num: this.layerNum,
        dataset: this.dataset,
        image_num: this.imageNum,
      };
      let response = await fetch(`${this.apiUrl}/layer_out`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify(payload),
      });
      this.featureMaps = await response.json();
      this.imager();
      this.loading = false;
    },
    dragMouseDown: function (event) {
      event.preventDefault();
      // get the mouse cursor position at startup:
      this.positions.clientX = event.clientX;
      this.positions.clientY = event.clientY;
      document.onmousemove = this.elementDrag;
      document.onmouseup = this.closeDragElement;
    },
    elementDrag: function (event) {
      event.preventDefault();
      this.positions.movementX = this.positions.clientX - event.clientX;
      this.positions.movementY = this.positions.clientY - event.clientY;
      this.positions.clientX = event.clientX;
      this.positions.clientY = event.clientY;
      // set the element's new position:
      this.$refs.draggableContainer.style.top = this.$refs.draggableContainer.offsetTop - this.positions.movementY + "px";
      this.$refs.draggableContainer.style.left = this.$refs.draggableContainer.offsetLeft - this.positions.movementX + "px";
    },
    closeDragElement() {
      document.onmouseup = null;
      document.onmousemove = null;
    },
  },
  computed: {},
};
</script>

<style lang="scss">
// container handles
.draggable-container {
  top: auto;
  position: fixed;
  z-index: 9;
}
.draggable-header {
  cursor: move;
  z-index: 10;
}
.wrapper-container {
  width: 400px;
  min-width: 280px;
  min-height: 100px;
  resize: both;
  overflow: hidden;
}
.wrapper-constrain-height {
  max-height: calc(50vh);
}
.unlocked-height {
  height: calc(50vh);
}
.inner-content {
  //position: relative;
  max-height: -webkit-calc(100% - 35px);
  max-height: -moz-calc(100% - 35px);
  max-height: calc(50vh - 35px);
  overflow: auto;
}
.inner-content-max-height {
  //position: relative;
  max-height: -webkit-calc(100% - 35px);
  max-height: -moz-calc(100% - 35px);
  max-height: calc(100% - 35px);
  overflow: auto;
}

// control css
.fla-controls {
  position: absolute !important;
}

//image css stylings
.img-wrapper {
  display: inline;
}

$transition-duration: 0.1s;
.img-feature {
  border-radius: 2px;
  border-style: solid;
  border-width: 0px;
  background-color: #ff9800;
  border-color: #ff9800;
  -webkit-transition: border $transition-duration ease-in;
  -moz-transition: border $transition-duration ease-in;
  -o-transition: border $transition-duration ease-in;
  transition: border $transition-duration ease-in;
}

.img-feature-selected {
  border-radius: 2px;
  border-style: solid;
  border-width: 4px;
  background-color: #ff9800;
  border-color: #ff9800;
  -webkit-transition: border $transition-duration ease-out;
  -moz-transition: border $transition-duration ease-out;
  -o-transition: border $transition-duration ease-out;
  transition: border $transition-duration ease-out;
}
.noselect {
  -webkit-touch-callout: none; /* iOS Safari */
  -webkit-user-select: none; /* Safari */
  -khtml-user-select: none; /* Konqueror HTML */
  -moz-user-select: none; /* Old versions of Firefox */
  -ms-user-select: none; /* Internet Explorer/Edge */
  user-select: none; /* Non-prefixed version, currently
                                  supported by Chrome, Edge, Opera and Firefox */
}

.flex-wrapper {
  flex-wrap: wrap;
}
.feature-map-conv2d {
  image-rendering: pixelated;
  display: inline-block;
  //box-sizing: border-box;
  width: calc(25% - 8px);
}
.feature-map-linear {
  image-rendering: pixelated;
  width: 30px;
  float: left;
}

//scrollbar options
/* width */
::-webkit-scrollbar {
  width: 15px;
}
/* Track */
::-webkit-scrollbar-track {
  background: #585858;
}
/* Handle */
::-webkit-scrollbar-thumb {
  background: rgb(165, 165, 165);
}
/* Handle on hover */
::-webkit-scrollbar-thumb:hover {
  background: rgb(218, 218, 218);
}
::-webkit-scrollbar-corner {
  background: #555;
}
@keyframes metronome {
  from {
    transform: scale(0.1);
  }

  to {
    transform: scale(1);
  }
}

.metronome-animation {
  animation-name: metronome;
  animation-iteration-count: infinite;
  animation-direction: alternate;
  animation-duration: 1s;
}

.btn-fix:focus::before {
  opacity: 0 !important;
}
</style>