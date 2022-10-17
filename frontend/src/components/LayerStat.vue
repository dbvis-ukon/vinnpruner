<template>
  <div>
    <div :id="'container' + networkId"></div>
  </div>
</template>

<script>
import * as d3 from "d3";
export default {
  data() {
    return {
      d3Data: {},
      customBase: {},
      context: {},
      count: 5000,
      width: 750,
      height: 100,
      groupSpacing: 3,
      cellSpacing: 0,
      squareSize: 12,
      rows: 15,
    };
  },
  computed: {
    cellSize: function () {
      return Math.floor((this.width - 11 * this.groupSpacing) / (5 * this.squareSize * 2)) - this.cellSpacing;
    },
  },
  mounted() {
    console.log(d3);
    //this.d3Data = d3.range(this.count);
    this.createCanvas();
  },
  methods: {
    draw() {
      console.log("start drawing");
      this.context.clearRect(0, 0, this.width, this.height); // Clear the canvas.
      let custom = d3.select(this.customBase);
      let elements = custom.selectAll("custom.rect");
      let innerContext = this.context;
      elements.each(function () {
        var node = d3.select(this); // This is each individual element in the loop.
        innerContext.fillStyle = node.attr("fillStyle"); // Here you retrieve the colour from the individual in-memory node and set the fillStyle for the canvas paint
        /*console.log(
          `x: ${node.attr("x")} y: ${node.attr("y")} width: ${node.attr(
            "width"
          )} height: ${node.attr("height")}`
        );*/
        innerContext.fillRect(node.attr("x"), node.attr("y"), node.attr("width"), node.attr("height")); // Here you retrieve the position of the node and apply it to the fillRect context function which will fill and paint the square.
      });
      console.log("finish");
    },
    bindData(data) {
      /*let colorScale = d3.scaleSequential(d3.interpolateSpectral).domain(
        d3.extent(data, function (d) {
          return d;
        })
      );*/
      let colorScale = function (d) {
        if (d == 1) {
          return "#E1E1E1";
        } else {
          //return "#000000";
          return "#C44040";
        }
      };
      this.customBase = document.createElement("custom");
      let custom = d3.select(this.customBase);
      let join = custom.selectAll("custom.rect").data(data);
      var enterSel = join
        .enter()
        .append("custom")
        .attr("class", "rect")
        .attr(
          "x",
          function (d, i) {
            let squariness = this.squareSize > 10 ? this.squareSize : 10;
            let x0 = Math.floor(i / (this.squareSize * squariness)) % this.rows;
            let x1 = Math.floor(i % this.squareSize);
            return this.groupSpacing * x0 + (this.cellSpacing + this.cellSize) * (x1 + x0 * this.squareSize);
          }.bind(this)
        )
        .attr(
          "y",
          function (d, i) {
            let squariness = this.squareSize > 10 ? this.squareSize : 10;
            let y0 = Math.floor(i / (this.squareSize * squariness * this.rows));
            let y1 = Math.floor((i % (this.squareSize * squariness)) / squariness);
            return this.groupSpacing * y0 + (this.cellSpacing + this.cellSize) * (y1 + y0 * this.squareSize);
          }.bind(this)
        )
        .attr("width", this.cellSize)
        .attr("height", this.cellSize)
        .attr("fillStyle", function (d) {
          return colorScale(d);
        });
      /**
      join
        .merge(enterSel)
        .transition()
        .attr("width", this.cellSize)
        .attr("height", this.cellSize)
        .attr("fillStyle", function (d) {
          return colorScale(d);
        });
         */
      // exit
      //join.exit().transition().attr("width", 0).attr("height", 0).remove();
    },
    createCanvas() {
      const canvas = d3
        .select(`#container${this.networkId}`)
        .append("canvas")
        .attr("width", this.width)
        .attr("height", this.height)
        .attr("class", "d3canvas");
      this.context = canvas.node().getContext("2d");
    },
    arrayDepth(arr) {
      return (
        1 +
        (arr instanceof Array
          ? arr.reduce(
              function (max, item) {
                return Math.max(max, this.arrayDepth(item));
              }.bind(this),
              0
            )
          : -1)
      );
    },
  },
  props: {
    networkId: String,
    mask: Array,
  },
  watch: {
    mask: function () {
      if (this.mask) {
        this.squareSize * this.d3Data;
        this.d3Data = this.mask.flat(this.arrayDepth(this.mask));
        let canvasHeight =
          (this.cellSize * this.squareSize + this.groupSpacing) * Math.ceil(this.d3Data.length / (this.squareSize ** 2 * this.rows));
        //let canvasWidth = this.cellSize * this.squareSize * this.rows + this.rows * this.groupSpacing;
        //d3.select(`#container${this.networkId} > canvas`).attr("width", canvasWidth);
        d3.select(`#container${this.networkId} > canvas`).attr("height", canvasHeight);
        this.bindData(this.d3Data);
        this.draw();
      }
    },
  },
};
</script>
<style lang="scss">
.d3canvas {
  width: 100%;
}
</style>