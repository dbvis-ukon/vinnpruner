<template>
  <div :id="'webgl-container' + networkId">"></div>
</template>
<script>
import * as THREE from 'three'

export default {
  props: {
    networkId: String,
  },
  data() {
    return {
      cube: null,
      renderer: null,
      scene: null,
      camera: null
    }
  },
  methods: {
    init: function() {
      let container = document.querySelector('#lo-container');
      this.scene = new THREE.Scene()
      this.camera = new THREE.PerspectiveCamera(
        75,
        window.innerWidth / window.innerHeight,
        0.1,
        1000
      )

      this.renderer = new THREE.WebGLRenderer()
      this.renderer.setSize(700, 400)
      container.appendChild(this.renderer.domElement)

      const geometry = new THREE.BoxGeometry(1, 1, 1)
      const material = new THREE.MeshBasicMaterial({ color: 0x00ff00 })
      this.cube = new THREE.Mesh(geometry, material)
      this.scene.add(this.cube)

      this.camera.position.z = 5

      const animate = function() {}
    },
    animate: function() {
      requestAnimationFrame(this.animate)

      this.cube.rotation.x += 0.01
      this.cube.rotation.y += 0.01

      this.renderer.render(this.scene, this.camera)
    }
  },
  mounted() {
    this.init()
    this.animate()
  }
}
</script>