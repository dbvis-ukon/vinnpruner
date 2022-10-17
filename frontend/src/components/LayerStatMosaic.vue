<template lang="pug">
.mosaic-wrapper
  .brush-controls.ma-2.d-flex
    v-tooltip(top)
      template(v-slot:activator="{ on, attrs }")
        v-btn(
          outlined,
          color="grey darken-1",
          icon,
          large,
          v-bind="attrs",
          v-on="on",
          @click="toggleMode",
          :class="{ 'disable-events': keyDown }"
        )
          v-icon(v-if="modeBrushing") mdi-brush
          v-icon(v-else-if="!modeBrushing") mdi-cursor-move
      div
        p.font-weight-medium.pb-0.mb-0
          | Current mode:
          span.overline.pl-1 {{ modeBrushing ? 'Brush' : 'Move' }}
        span.font-weight-medium
          | Press
          span.overline.pl-1.pr-1 CTRL
          | or click to toggle modes
        p.font-weight-medium.pb-0.mb-0(v-if="modeBrushing")
          | Hold
          span.overline.pl-1.pr-1 SHIFT
          | to move
  .mosaic-container(
    :id="'ls_' + networkId",
    @keydown.16="toggleMode",
    @keyup.16="toggleMode",
    @keydown.17="toggleMode",
    tabindex="0",
    @focus="updateFocus",
    @focusout="updateFocus"
  )
    svg(:id="`cnv_${networkId}`")
</template>

<script>
import * as d3 from "d3";

export default {
  mounted() {
    if (this.initialBrush) {
      this.lastBrush = this.initialBrush.brushSnapshot;
    }
    this.updateScaleFactors();
    this.init();
    if (this.modeBrushing) {
      this.registerBrush();
    } else {
      this.registerZoomAndPan();
    }
  },
  props: {
    mosaics: Array,
    layerType: String,
    imHeight: Number,
    imWidth: Number,
    networkId: String,
    chunkWidth: Number,
    chunksPerSlice: Number,
    containerWidth: Number,
    initialBrush: Object,
  },
  data() {
    return {
      // viewbox & svg definitions
      //viewBox: { x: 0, y: 0, w: this.width, h: this.mosaics.length * this.imHeight },
      viewBox: { x: 0, y: 0, w: 0, h: 0 },
      svg: {},
      images: {},
      selectedIndexes: [],

      // d3 scales
      yScale: {},
      xScale: {},

      // data about selected custom mask
      modePruning: true,
      selectedChannels: [],
      selectedKernels: [],

      // scale and render data
      renderModeThreshold: 11,
      renderModeThresholdLinear: 2,
      minHeight: 400,
      constrainWidth: 180,
      widthConstrained: false,
      widthScaleFactor: 1,
      heightConstrainScaleFactor: 1,
      containerScaleFactor: 1,

      // constrol management variables
      modeBrushing: true,
      keyDown: false,
      hasFocus: false,
      controlMode: false,
      lastBrush: undefined,

      // events for zoomer and mover
      moveStartPoint: { x: 0, y: 0 },
      moveEndpoint: { x: 0, y: 0 },
      isPanning: false,
      zoomValue: 1,
      scale: 1,
      mouseDownEvent: undefined,
      mouseMoveEvent: undefined,
      mouseWheelEvent: undefined,
      mouseUpEvent: undefined,
      eventContainer: undefined,
    };
  },
  computed: {
    brushClass() {
      return `${this.networkId}-brush`;
    },
    brushHoldClass() {
      return `${this.networkId}-brush-hold`;
    },
    height() {
      return this.mosaics.length * this.imHeight;
    },
    width() {
      return this.imWidth;
    },
    renderModeThresholdReached() {
      if (this.layerType.toLowerCase().includes("conv")) {
        return this.scale * (this.chunkWidth * this.containerScaleFactor) > this.renderModeThreshold;
      } else {
        return this.scale * (this.chunkWidth * this.containerScaleFactor) > this.renderModeThresholdLinear;
      }
    },
  },
  watch: {
    scale() {
      if (this.renderModeThresholdReached) {
        this.svg.selectAll("image").attr("class", "pixel-render");
      } else {
        this.svg.selectAll("image").attr("class", "speed-render");
      }
    },
    hasFocus() {},
  },
  methods: {
    setBrushDescription() {},
    updateFocus(event) {
      if (event.type == "focus") {
        this.hasFocus = true;
      } else if (event.type == "focusout") {
        this.hasFocus = false;
      }
    },
    updateScaleFactors() {
      let divWidth = document.getElementById("ls_" + this.networkId).clientWidth;
      let widthScaleFactor = divWidth / this.width;
      let scaledHeight = widthScaleFactor * this.height;
      let heightConstrainScaleFactor = scaledHeight / window.innerHeight;
      let isConstrained = scaledHeight > innerHeight;

      this.widthScaleFactor = widthScaleFactor;
      this.heightConstrainScaleFactor = heightConstrainScaleFactor;

      if (!isConstrained) {
        this.containerScaleFactor = widthScaleFactor;
      } else {
        this.containerScaleFactor = widthScaleFactor / heightConstrainScaleFactor;
      }

      console.log(
        `mosaic rendering information\nw: ${this.width}, sw: ${Math.ceil(this.width * widthScaleFactor)},`,
        `h: ${this.height}, sh: ${Math.ceil(scaledHeight)},`,
        `ih: ${window.innerHeight}, dw: ${divWidth}, wsf: ${widthScaleFactor.toFixed(4)},`,
        `hsf: ${heightConstrainScaleFactor.toFixed(2)}, ic: ${isConstrained}, csf: ${this.containerScaleFactor.toFixed(2)}`
      );
    },
    toggleMode(event) {
      if (event && ((event.type == "keydown" && event.key == "Control") || event.type == "click") && !this.keyDown) {
        this.controlMode = !this.controlMode;
      } else if (event && event.type != "click" && !this.controlMode) {
        if (this.keyDown && event.type != "keyup") {
          return;
        }
        this.keyDown = !this.keyDown;
      } else if ((event && event.type == "keydown") || event.type == "keyup") {
        return;
      }

      this.modeBrushing = !this.modeBrushing;
      if (this.modeBrushing) {
        this.removeZoomAndPan();
        this.registerBrush();
      } else {
        this.removeBrush();
        this.registerZoomAndPan();
      }
    },
    init() {
      this.viewBox = { x: 0, y: 0, w: this.width, h: this.mosaics.length * this.imHeight };
      this.svg = d3
        .select(`#cnv_${this.networkId}`)
        .attr("class", "d3-canvas")
        .attr("id", `cnv_${this.networkId}`)
        .attr("width", this.width)
        .attr("viewBox", `0 0 ${this.width} ${this.mosaics.length * this.imHeight}`)
        .attr("preserveAspectRatio", "xMidYMin meet");

      const scaledHeight = this.height * this.widthScaleFactor;
      if (scaledHeight < this.minHeight) {
        this.svg.attr("height", this.minHeight)
      }

      this.yScale = d3.scaleLinear().domain([this.mosaics.length, 0]).range([this.height, 0]);
      this.xScale = d3.scaleLinear().domain([0, this.chunksPerSlice]).range([0, this.width]);

      this.images = this.svg
        .selectAll("image")
        .data(this.mosaics)
        .enter()
        .append("svg:image")
        .attr("xlink:href", function (d, i) {
          return `data:image/png;base64,${d}`;
        })
        .attr("width", this.width)
        .attr("height", this.imHeight)
        .attr(
          "y",
          function (d, i) {
            return i * this.imHeight;
          }.bind(this)
        )
        .attr(
          "class",
          function () {
            if (this.renderModeThresholdReached) {
              return "pixel-render";
            } else {
              return "speed-render";
            }
          }.bind(this)
        );
    },
    getSelectionByScale(event) {
      if (!event.sourceEvent) return;
      let extent = event.selection;
      this.lastBrush = extent;
      if (!extent) {
        return;
      }

      let top = extent[0][1];
      let bot = extent[1][1];
      let lef = extent[0][0];
      let rig = extent[1][0];

      // without snapping: floor top lef and ceil bot rig
      let topScaled = Math.round(this.yScale.invert(top));
      let botScaled = Math.round(this.yScale.invert(bot));
      let lefScaled = Math.round(this.xScale.invert(lef));
      let rigScaled = Math.round(this.xScale.invert(rig));

      if (event.type == "start" && lef == rig && top == bot) {
        console.log(`brush cleared`);
        this.$emit("brush-selection-changed", {
          channels: [0, 0],
          kernels: [0, 0],
          brushSnapshot: this.lastBrush,
          remove: true,
        });
      }

      if (event.type == "end") {
        //this.selectedChannels = [...Array(botScaled - topScaled).keys()].map((e) => e + topScaled);
        //this.selectedKernels = [...Array(rigScaled - lefScaled).keys()].map((e) => e + lefScaled);
        this.selectedChannels = [topScaled, botScaled];
        this.selectedKernels = [lefScaled, rigScaled];

        console.log(`chans: ${this.selectedChannels} kerns: ${this.selectedKernels}`);
        this.$emit("brush-selection-changed", {
          channels: this.selectedChannels,
          kernels: this.selectedKernels,
          brushSnapshot: this.lastBrush,
        });
      }

      let topMapped = this.yScale(topScaled);
      let botMapped = this.yScale(botScaled);
      let lefMapped = this.xScale(lefScaled);
      let rigMapped = this.xScale(rigScaled);
      let mapped = [
        [lefMapped, topMapped],
        [rigMapped, botMapped],
      ];

      d3.select("." + this.brushClass).call(event.target.move, mapped);
    },
    registerBrush() {
      d3.selectAll("." + this.brushHoldClass).remove();
      const brush = d3
        .brush()
        .extent([
          [0, 0],
          [this.width, this.height],
        ])
        .on("brush start end", this.getSelectionByScale);
      d3.select(`#cnv_${this.networkId}`).append("g").attr("class", this.brushClass).call(brush);
      if (this.lastBrush) {
        d3.select("." + this.brushClass).call(brush.move, [this.lastBrush[0], this.lastBrush[1]]);
      }
    },
    removeBrush() {
      d3.select(`#cnv_${this.networkId}`).append("g").attr("class", this.brushHoldClass);
      const brushHoldClass = this.brushHoldClass;
      d3.selectAll(`.${this.brushClass} > .selection`).each(function (e) {
        let elem = d3.select(this);
        let x = elem.attr("x");
        let y = elem.attr("y");
        let w = elem.attr("width");
        let h = elem.attr("height");
        let fill = elem.attr("fill");
        d3.select("." + brushHoldClass)
          .append("rect")
          .attr("x", x)
          .attr("y", y)
          .attr("width", w)
          .attr("height", h)
          .attr("fill", fill)
          .attr("style");
      });

      d3.selectAll("." + this.brushClass).remove();
    },
    registerZoomAndPan() {
      this.eventContainer = document.getElementById(`cnv_${this.networkId}`);
      this.addMouseUpEvent();
      this.addMouseDownEvent();
      this.addMouseWheelEvent();
      this.addMouseMoveEvent();
    },
    removeZoomAndPan() {
      if (!this.eventContainer) return;
      this.eventContainer.removeEventListener("wheel", this.mouseWheelEvent, false);
      this.eventContainer.removeEventListener("mousewheel", this.mouseWheelEvent, false);
      this.eventContainer.removeEventListener("mousedown", this.mouseDownEvent, false);
      this.eventContainer.removeEventListener("mouseup", this.mouseUpEvent, false);
      this.eventContainer.removeEventListener("mousemove", this.mouseMoveEvent, false);
    },
    addMouseUpEvent() {
      this.mouseUpEvent = function (e) {
        if (this.isPanning) {
          this.moveEndpoint = { x: e.x, y: e.y };
          let dx = (this.moveStartPoint.x - this.moveEndpoint.x) / (this.scale * this.containerScaleFactor);
          let dy = (this.moveStartPoint.y - this.moveEndpoint.y) / (this.scale * this.containerScaleFactor);
          this.viewBox = { x: this.viewBox.x + dx, y: this.viewBox.y + dy, w: this.viewBox.w, h: this.viewBox.h };
          this.eventContainer.setAttribute("viewBox", `${this.viewBox.x} ${this.viewBox.y} ${this.viewBox.w} ${this.viewBox.h}`);
          this.isPanning = false;
        }
      }.bind(this);
      this.eventContainer.onmouseup = this.mouseUpEvent;
    },
    addMouseDownEvent() {
      this.scale = this.width / this.viewBox.w;
      this.mouseDownEvent = function (e) {
        this.updateScaleFactors();
        this.isPanning = true;
        this.moveStartPoint = { x: e.x, y: e.y };
      }.bind(this);
      this.eventContainer.addEventListener("mousedown", this.mouseDownEvent);
    },
    addMouseWheelEvent() {
      this.mouseWheelEvent = function (e) {
        e.preventDefault();
        //prevent zooming out if scale is smaller than original
        if (this.scale <= 1 && Math.sign(-e.deltaY) < 0) {
          return;
        }
        let w = this.viewBox.w;
        let h = this.viewBox.h;
        // let mx = e.offsetX; //mouse x
        // let my = e.offsetY;
        let dw = w * Math.sign(-e.deltaY) * 0.05;
        let dh = h * Math.sign(-e.deltaY) * 0.05;

        // default behavior
        // let dx = (dw * mx) / this.width;
        // let dy = (dh * my) / this.height;
        let dx = Math.sign(-e.deltaY) * this.viewBox.w * 0.025;
        let dy = Math.sign(-e.deltaY) * this.viewBox.h * 0.025;

        //only center width
        dy = 0;

        // translate to mouse pos
        // dx = Math.sign(-e.deltaY) * mx * 0.025;
        // dy = Math.sign(-e.deltaY) * my * 0.025;

        this.viewBox = { x: this.viewBox.x + dx, y: this.viewBox.y + dy, w: this.viewBox.w - dw, h: this.viewBox.h - dh };
        this.scale = this.width / this.viewBox.w;
        this.zoomValue = Math.round(this.scale * 100) / 100;
        this.eventContainer.setAttribute("viewBox", `${this.viewBox.x} ${this.viewBox.y} ${this.viewBox.w} ${this.viewBox.h}`);
      }.bind(this);
      this.eventContainer.addEventListener("mousewheel", this.mouseWheelEvent);
      this.eventContainer.addEventListener("wheel", this.mouseWheelEvent);
    },
    addMouseMoveEvent() {
      this.mouseMoveEvent = function (e) {
        if (this.isPanning) {
          this.moveEndpoint = { x: e.x, y: e.y };
          let dx = (this.moveStartPoint.x - this.moveEndpoint.x) / (this.scale * this.containerScaleFactor);
          let dy = (this.moveStartPoint.y - this.moveEndpoint.y) / (this.scale * this.containerScaleFactor);
          let movedViewBox = { x: this.viewBox.x + dx, y: this.viewBox.y + dy, w: this.viewBox.w, h: this.viewBox.h };
          this.eventContainer.setAttribute("viewBox", `${movedViewBox.x} ${movedViewBox.y} ${movedViewBox.w} ${movedViewBox.h}`);
        }
      }.bind(this);
      this.eventContainer.addEventListener("mousemove", this.mouseMoveEvent);
    },
  },
};
</script>

<style lang="scss">
.d3-canvas {
  width: 100%;
  max-height: 85vh;
}

.brush-controls {
  position: absolute;
  z-index: 1;
}

#control-text {
  pointer-events: none;
}

.disable-events {
  pointer-events: none;
}

.pixel-render {
  image-rendering: pixelated;
}
.speed-render {
  image-rendering: crisp-edges;
}
rect.selection {
  //fill: steelblue;
  fill: #c44040;
  fill-opacity: 0.9;
}
/*.handle {
  fill: #c44040;
  fill-opacity: 1;
}*/
.mosaic-container {
  overflow: hidden;
  position: relative;
  //box-shadow: 0px 0px 0px 1px rgba(150, 150, 150, 0.2);
}
.mosaic-wrapper {
  position: relative;
}
.mosaic-container:focus {
  outline: none;
  box-shadow: 0px 0px 0px 4px rgba(130, 130, 130, 0.2);
  border-radius: 2px;
}
</style>
