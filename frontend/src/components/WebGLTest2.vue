<template>
  <div>
    <canvas class="webgl-canvas" :id="'canvas_' + networkId"></canvas>
  </div>
</template>
<script>
import * as THREE from "three";

export default {
  props: {
    networkId: String,
  },
  data() {
    return {
      width: 750,
      height: 400,
      cube: null,
      renderer: null,
      scene: null,
      camera: null,
    };
  },
  methods: {
    init: function () {
      let circle_sprite = new THREE.TextureLoader().load("https://fastforwardlabs.github.io/visualization_assets/circle-sprite.png");
      const canvas = document.querySelector("#canvas_" + this.networkId);
      const fov = 40;
      const near = 10;
      const far = 1000;
      this.camera = new THREE.PerspectiveCamera(fov, this.width / this.height, near, far + 1);
      this.scene = new THREE.Scene();
      this.scene.background = new THREE.Color(0xefefef);

      this.renderer = new THREE.WebGLRenderer({ canvas });
      this.addPlaneCube(-10, 0, 0.3, circle_sprite);

      this.renderer.setSize(this.width, this.height);
      this.addPlaneCubes(circle_sprite);

      this.camera.position.z = 20;
      this.renderer.render(this.scene, this.camera);
    },

    addPlaneCubes: function (sprite) {
      const geometry = new THREE.Geometry();
      const color = new THREE.Color(0x00ff00);
      const material = new THREE.PointsMaterial({
        map: sprite,
        size: 10,
        sizeAttenuation: false,
        vertexColors: THREE.VertexColors,
      });
      let colors = [];

      let dist = 0.5;
      for (let i = 0; i < 250; i++) {
        let y = 6 - i * dist;
        for (let j = 0; j < 50; j++) {
          let x = -12.5 + j * dist;
          colors.push(color);
          const vertex = new THREE.Vector3(x, y, 0);
          geometry.vertices.push(vertex);
        }
      }
      geometry.colors = colors;
      const points = new THREE.Points(geometry, material);
      this.scene.add(points);
    },
    addPlaneCube: function (x, y, size, sprite) {
      /*const geometry = new THREE.PlaneGeometry(size, size);
      const material = new THREE.MeshBasicMaterial({ color: 0x00ff00 });
      const cube = new THREE.Mesh(geometry, material);
      this.scene.add(cube);
      cube.position = new THREE.Vector3(x, y, 1);
      */

      const geometry = new THREE.Geometry();
      const vertex = new THREE.Vector3(x, y, 0);
      geometry.vertices.push(vertex);
      const color = new THREE.Color(0x00ff00);
      geometry.colors = [color];
      const material = new THREE.PointsMaterial({
        map: sprite,
        size: size,
        sizeAttenuation: false,
        vertexColors: THREE.VertexColors,
      });
      const points = new THREE.Points(geometry, material);

      this.scene.add(points);
    },
  },

  mounted() {
    this.init();
  },
};
</script>

<style scoped>
.webgl-canvas {
  width: 100%;
  display: block;
}
</style>