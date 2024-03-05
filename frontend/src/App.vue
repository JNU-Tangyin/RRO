<template>
    <canvas id="render-canvas"></canvas>
    <div class="analysis-info">
        <div class="current-time">Current time：{{ gameInfo.current_time }}</div>
        <a-row>
            <a-col class="data-row">
                <div class="analysis-title">Used rate</div>
                <div class="analysis-data">{{ `${gameInfo.used_rate.toFixed(2)}%` }}</div>
            </a-col>
            <a-col class="data-row">
                <div class="analysis-title">Relocation times</div>
                <div class="analysis-data">{{ gameInfo.reload_count }}</div>
            </a-col>
            <a-col class="data-row">
                <div class="analysis-title">Twice relocation times</div>
                <div class="analysis-data">{{ gameInfo.reload_twice_count }}</div>
            </a-col>
            <a-col class="data-row">
                <div class="analysis-title">Crane bridge distance</div>
                <div class="analysis-data">{{ gameInfo.huge_car_dist }}</div>
            </a-col>
            <a-col class="data-row">
                <div class="analysis-title">Crane crab distance</div>
                <div class="analysis-data">{{ gameInfo.mini_car_dist }}</div>
            </a-col>
            <a-col class="data-row">
                <div class="analysis-title">Machine position</div>
                <div class="analysis-data">{{ gameInfo.mc_last_position }}</div>
            </a-col>
            <a-col class="data-row">
                <div class="analysis-title">Reward</div>
                <div class="analysis-data">{{ gameInfo.total_reward.toFixed(2) }}</div>
            </a-col>
        </a-row>
    </div>
    <div class="container-info" v-if="containerList.length > 0">
        <a-row class="container-main-info">
            <a-col :span="3">
                <template v-if="parseInt(currentContainer.CONTAINER_TYPE, 10) === 20">
                    <img class="container-img" src="c20.png" alt="">
                </template>
                <template v-if="parseInt(currentContainer.CONTAINER_TYPE, 10) === 40">
                    <img class="container-img" src="c40.png" alt="">
                </template>
            </a-col>
            <a-col :span="21" class="container-box">
                <div class="container-base-info">
                    {{ currentContainer.CONTAINER_NO }} {{
                        currentContainer.CONTAINER_TYPE
                    }} {{ currentContainer.CONTAINER_STATE === '重' ? 'Heavy' : 'Empty' }}
                    <template v-if="currentContainer.ACTION === 'leave'">
                        {{ getBoxByContainerRefId(currentContainer.CONTAINER_REF_ID).containerInfo.PILE_PLACE }}
                    </template>
                    <template v-if="currentContainer.ACTION === 'move'">
                        {{ currentMovePile }}
                    </template>
                </div>
                <div class="tag-wrp">
                    <span class="import-tag">{{ currentContainer.IMPORT_OR_EXPORT === '进' ? 'Import' : 'Export' }}</span>
                    <span class="inside-tag">
                        {{ currentContainer.INSIDE_OR_OUTSIDE === '内' ? 'Domestic' : 'Foreign' }} Trade
                    </span>
                    <span class="pack-tag">{{
                            currentContainer.BILL_LADING_REF_ID ? (container_bill_map[currentContainer['CONTAINER_REF_ID']].length > 1 ? 'LCL' : 'FCL') : 'none'
                        }}</span>
                    <span class="used-tag" v-if="currentContainer.IF_USED === 'Y'">Completed Docs</span>
                    <span class="check-tag" v-if="currentContainer.IF_CHECK === 'Y'">Customs Inspection</span>
                    <span class="bind-tag" v-if="currentContainer.IF_BIND === 'Y'">Binded Task</span>
                    <span class="book-tag" v-if="currentContainer.IF_BOOK === 'Y'">Booked InGate</span>
                    <span class="action-tag">
                        <template v-if="currentContainer.ACTION === 'move'">Move</template>
                        <template v-if="currentContainer.ACTION === 'enter'">Enter</template>
                        <template v-if="currentContainer.ACTION === 'leave'">Leave</template>
                    </span>
                </div>
            </a-col>
        </a-row>
        <div class="detail-info">
            <div class="detail-title">In Date：{{ currentContainer.IN_DATE }}</div>
            <template v-if="(currentContainer.ACTION === 'move' || currentContainer.ACTION === 'enter') &&  currentContainer.IMPORT_OR_EXPORT === '进'">
                <div class="detail-title">Predict Date：{{ currentContainer.PRE_DATE }}</div>
            </template>
            <div class="detail-title">Controlling Company：{{ currentContainer.CNTR_ADMIN_NAME }}</div>
            <div class="detail-title">Owning Company：{{ currentContainer.CNTR_OWNER_NAME }}</div>
            <template v-for="(item, index) in container_bill_map[currentContainer.CONTAINER_REF_ID]" :key="index">
                <div class="detail-title">Bill Lading Info：{{ item.BILL_LADING_NO }}</div>
                <div class="goods-box">
                    <div class="info-space">
                        <a-space>
                            <span>{{ item.GOODS_IN_CHINESE }}</span>
                            <span>{{ item.TOTAL_PACKAGES }}piece</span>
                            <span>{{ item.TOTAL_WEIGHT }}kg</span>
                            <!--<span>{{ item.TOTAL_KINDS_PACKAGE }}</span>
                            <span>{{ item.GOODS_KINDS }}</span>-->
                        </a-space>
                    </div>
                    <div class="info-space">
                        <a-space>
                            <span>Cargo Owner：{{ item.CONSIGNOR_NAME }}</span>
                        </a-space>
                    </div>
                    <div class="info-space">
                        <a-space>
                            <span>Payer：{{ item.CONSIGNOR_NAME }}</span>
                        </a-space>
                    </div>
                </div>
            </template>
            <div class="next-container" @click="nextContainer">→</div>
        </div>
    </div>
</template>

<script>
import {defineComponent} from 'vue'
import * as BABYLON from 'babylonjs'

const box_width = 2
const box_height = 1
const box_depth = 1

let scene, canvas, engine, current_block
let boxList = []
let boxMap = []
let towerMap = {}
let camera

const yard_area = '01'
const yard_width = 16
const yard_height = 15
const yard_depth = 4
const init_date = '2021-08-21 20:46:56'
const target_date = '2021-08-25 23:59:58'
const multi_bay = true
const current_bay = 2
const container_size = 40
const ws_host = 'ws://localhost:7788'
const ground_width = 2 * yard_width + 6
const ground_height = 1 * yard_height + 3

let ws

export default defineComponent({
    name: 'App',
    data() {
        return {
            container_bill_map: {},
            current_container_map: {},
            containerList: [],
            score: 0,
            scoreRecord: [],
            currentMovePile: undefined,
            ableNext: true,
            totalReload: 0,
            usedRate: 0,
            hugeCarDist: 0,
            smallCarDist: 0,
            lastPile: undefined,
            showMask: false,
            detailContainer: {},
            currentTime: undefined,
            preMap: {},
            gameInfo: {
                used_rate: 0,
                total_reward: 0
            },
            customPilePlace: undefined
        }
    },
    computed: {
        currentContainer(ov, nv) {
            const self = this
            const currentContainer = self.containerList[0] || {}
            return currentContainer
        }
    },
    mounted() {
        const self = this
        canvas = document.getElementById('render-canvas')
        engine = new BABYLON.Engine(canvas, true)
        const createScene = () => {
            scene = new BABYLON.Scene(engine)
            scene.clearColor = new BABYLON.Color4.FromHexString("#061e38FF")

            self.addGround()
            camera = self.addCamera()
            self.addLight()
            ws = new WebSocket(`${ws_host}/ws/create_docker_game`)
            ws.onopen = function (e) {
                ws.send(JSON.stringify({
                    r_type: 'create_game',
                    area: yard_area,
                    bay: yard_width,
                    row: yard_height,
                    height: yard_depth,
                    init_date,
                    target_date,
                    multi_bay,
                    current_bay,
                    container_size
                }))
            }
            ws.onmessage = function (event) {
                if (event.data) {
                    const result = JSON.parse(event.data)
                    if (result.data.init) {
                        const container_map = result.data.current_container_map
                        for (const ref_id of Object.keys(container_map)) {
                            const container = container_map[ref_id]
                            self.addContainer(container)
                        }
                        self.current_container_map = result.data.current_container_map
                        self.containerList = result.data.operation_list
                        self.gameInfo = result.data.game_info
                        self.container_bill_map = result.data.container_bill_map
                        towerMap = result.data.yard_stack_map
                        self.curCtnColor(self.containerList[0].CONTAINER_REF_ID)
                    } else if (result.data.step) {
                        const last_operation = JSON.parse(JSON.stringify(self.containerList[0]))
                        const current_operation = result.data.operation_list[0]
                        self.current_container_map = result.data.current_container_map
                        self.containerList = result.data.operation_list
                        self.gameInfo = result.data.game_info
                        towerMap = result.data.yard_stack_map
                        self.resetBoxList()
                        self.curCtnColor(self.containerList[0].CONTAINER_REF_ID)
                        if (result.data.action_info.success) {
                            if (result.data.action_info.action_type === 'move') {
                                const currentBox = self.getBoxByContainerRefId(last_operation['CONTAINER_REF_ID'])
                                currentBox.dispose()
                                if (result.data.action_info.enter_able_pile && self.currentContainer.ACTION === 'move') {
                                    result.data.action_info.enter_able_pile.forEach((pItem) => {
                                        const temCtnInfo = JSON.parse(JSON.stringify(self.currentContainer))
                                        temCtnInfo.PILE_PLACE = pItem
                                        const material = new BABYLON.StandardMaterial('boxMat', scene)
                                        material.alpha = 0.6
                                        material.diffuseColor = new BABYLON.Color4.FromHexString('#b8ff42FF')
                                        const currentBox = self.addContainer(temCtnInfo, material)
                                        currentBox.tempPicker = true
                                    })
                                }
                                last_operation['PILE_PLACE'] = result.data.action_info.pile_place
                                self.addContainer(last_operation)
                            } else if (result.data.action_info.action_type === 'leave') {
                                const currentBox = self.getBoxByContainerRefId(last_operation['CONTAINER_REF_ID'])
                                currentBox.dispose()
                                if (result.data.action_info.enter_able_pile && self.currentContainer.ACTION === 'enter') {
                                    result.data.action_info.enter_able_pile.forEach((pItem) => {
                                        const temCtnInfo = JSON.parse(JSON.stringify(self.currentContainer))
                                        temCtnInfo.PILE_PLACE = pItem
                                        const material = new BABYLON.StandardMaterial('boxMat', scene)
                                        material.alpha = 0.6
                                        material.diffuseColor = new BABYLON.Color4.FromHexString('#b8ff42FF')
                                        const currentBox = self.addContainer(temCtnInfo, material)
                                        currentBox.tempPicker = true
                                    })
                                }
                            } else if (result.data.action_info.action_type === 'enter') {
                                last_operation['PILE_PLACE'] = result.data.action_info.pile_place
                                self.addContainer(last_operation)
                                if (result.data.action_info.enter_able_pile && self.currentContainer.ACTION === 'enter') {
                                    result.data.action_info.enter_able_pile.forEach((pItem) => {
                                        const temCtnInfo = JSON.parse(JSON.stringify(self.currentContainer))
                                        temCtnInfo.PILE_PLACE = pItem
                                        const material = new BABYLON.StandardMaterial('boxMat', scene)
                                        material.alpha = 0.6
                                        material.diffuseColor = new BABYLON.Color4.FromHexString('#b8ff42FF')
                                        const currentBox = self.addContainer(temCtnInfo, material)
                                        currentBox.tempPicker = true
                                    })
                                }
                            }
                        } else {
                            if (result.data.action_info.action_type === 'leave') {
                                self.$message.warn('Please solve the relocation container')
                                result.data.action_info.enter_able_pile.forEach((pItem) => {
                                    const temCtnInfo = JSON.parse(JSON.stringify(self.currentContainer))
                                    temCtnInfo.PILE_PLACE = pItem
                                    const material = new BABYLON.StandardMaterial('boxMat', scene)
                                    material.alpha = 0.6
                                    material.diffuseColor = new BABYLON.Color4.FromHexString('#b8ff42FF')
                                    const currentBox = self.addContainer(temCtnInfo, material)
                                    currentBox.tempPicker = true
                                })
                                result.data.action_info.block_container_id.forEach((cItem) => {
                                    const currentBox = self.getBoxByContainerRefId(cItem.CONTAINER_REF_ID)
                                    currentBox.material.diffuseColor = new BABYLON.Color3(1, 0, 0)
                                    currentBox.isMove = true
                                })
                            } else if (result.data.action_info.action_type === 'duplicate') {
                                console.warn('Data error')
                                result.data.action_info.enter_able_pile.forEach((pItem) => {
                                    const temCtnInfo = JSON.parse(JSON.stringify(self.currentContainer))
                                    temCtnInfo.PILE_PLACE = pItem
                                    const material = new BABYLON.StandardMaterial('boxMat', scene)
                                    material.alpha = 0.6
                                    material.diffuseColor = new BABYLON.Color4.FromHexString('#b8ff42FF')
                                    const currentBox = self.addContainer(temCtnInfo, material)
                                    currentBox.tempPicker = true
                                })
                            }
                        }
                    }
                }
            }

        }

        createScene()
        engine.runRenderLoop(() => {
            scene.render()
        })
        window.addEventListener('resize', function () {
            engine.resize()
        })

      document.addEventListener('keydown', function(event) {
            if (event.keyCode === 32) {
                self.nextContainer()
            }
        })
    },
    methods: {
        curCtnColor () {
            const self = this
            const currentBox = self.getBoxByContainerRefId(self.containerList[0].CONTAINER_REF_ID)
            if (self.containerList[0].ACTION === 'leave') {
                currentBox.material.diffuseColor = new BABYLON.Color4.FromHexString('#91003fff')
                currentBox.isCurrent = true
            }
        },
        addGround() {
            const yardMat = new BABYLON.StandardMaterial("yardMat")
            yardMat.diffuseColor = new BABYLON.Color3.FromHexString('#8ae9ff')

            const ground = new BABYLON.MeshBuilder.CreateGround("ground", {width: ground_width, height: ground_height})

            const textureGround = new BABYLON.DynamicTexture("dynamic texture", {
                width: ground_width,
                height: ground_height
            }, scene);
            const font = "bold 80px 黑体";
            textureGround.drawText("01 Container Block", 60, 120, font, "black", "white", true, true);
            yardMat.diffuseTexture = textureGround
            ground.material = yardMat

            return ground
        },
        addCamera() {
            const camera = new BABYLON.ArcRotateCamera("camera", -3 * Math.PI / 4, Math.PI / 2.5, 50, new BABYLON.Vector3(0, 0, 0));
            camera.attachControl(canvas, true);
            return camera
        },
        addLight() {
            const light = new BABYLON.HemisphericLight("light", new BABYLON.Vector3(1, 1, 0));
            return light
        },
        addContainer(container, material) {
            const self = this
            if (!material) {
                material = new BABYLON.StandardMaterial('boxMat', scene)
                material.alpha = 0.8
            }
            const containerType = parseInt(container.CONTAINER_TYPE.substr(0, 2), 10)
            const containerBay = parseInt(container.PILE_PLACE.substr(2, 2))
            const containerRow = parseInt(container.PILE_PLACE.substr(4, 2))
            const containerLayer = parseInt(container.PILE_PLACE.substr(6, 1))
            let box
            const meshId = `box_${container.PILE_PLACE}`
            if (containerType === 20) {
                const bayCount = (containerBay + 1) / 2
                box = new BABYLON.MeshBuilder.CreateBox(meshId, {
                    width: box_width,
                    height: box_height,
                    depth: box_depth
                })
                box.position.x = -yard_width * box_width / 2 + box_width / 2 + (bayCount - 1) * box_width
                box.position.z = -(-yard_height * box_depth / 2 + box_depth / 2 + (containerRow - 1) * box_depth)
                box.position.y = box_height / 2 + (containerLayer - 1) * box_height
            } else {
                const bayCount = containerBay / 2
                box = new BABYLON.MeshBuilder.CreateBox(meshId, {
                    width: 2 * box_width,
                    height: box_height,
                    depth: box_height
                })
                box.position.x = -yard_width * box_width / 2 + box_width + (bayCount - 1) * box_width
                box.position.z = -(-yard_height * box_depth / 2 + box_depth / 2 + (containerRow - 1) * box_depth)
                box.position.y = box_height / 2 + (containerLayer - 1) * box_height
            }
            box.material = material
            box.enableEdgesRendering()
            box.edgesWidth = 0.0
            box.containerInfo = container
            boxList.push(box)
            boxMap[meshId] = box
            self.initBoxPickEvent(box)
            return box
        },
        initBoxPickEvent (box) {
            box.isPickable = true
            box.actionManager = new BABYLON.ActionManager(scene)
            box.actionManager.registerAction(
                    new BABYLON.ExecuteCodeAction(
                            BABYLON.ActionManager.OnPickTrigger, function (evt) {
                                if (box.tempPicker) {
                                    ws.send(JSON.stringify({
                                        r_type: 'take_action',
                                        input_pile: box.containerInfo.PILE_PLACE
                                    }))
                                }
                            }
                    )
            )
        },
        getBoxByContainerRefId(refId) {
            let item
            for (let i = 0; i < boxList.length; i++) {
                item = boxList[i]
                if (item.containerInfo.CONTAINER_REF_ID === refId) {
                    break
                }
            }
            return item
        },
        resetBoxList() {
            const newList = []
            boxList.forEach((item) => {
                if (!item._isDisposed) {
                    if (item.tempPicker) {
                        item.dispose()
                    } else {
                        if (!item.isMove && !item.isCurrent) {
                            item.edgesWidth = 0.0
                            item.material.diffuseColor = new BABYLON.Color4(1, 1, 1)
                            item.isPicked = false
                            item.alpha = 1
                        }
                        newList.push(item)
                    }
                }
            })
            boxList = newList

        },
        nextContainer() {
            const self = this
            if (self.ableNext) {
                ws.send(JSON.stringify({
                    r_type: 'take_action'
                }))
            }
        }
    }
})
</script>

<style lang="scss">
#app {
    height: 100%;
}

* {
    margin: 0;
    padding: 0;
}

html, body {
    height: 100%;
}

#render-canvas {
    width: 100%;
    height: 100%;
}

.pile-panel {
    height: 100%;
}

.pile-panel-item {
    height: 100%;
    overflow: auto;

    .ctn-item {
        padding: 12px;
        cursor: pointer;

        &:hover {
            background-color: rgba(#284123, 0.4);
        }
    }
}

.ant-list-items {
    border-bottom: 1px solid #e4e4e4;
}

.current-title {
    padding: 12px;
    border-bottom: 1px solid #e4e4e4;
}

.container-info {
    width: 560px;
    position: fixed;
    right: 40px;
    bottom: 40px;
    background-color: rgba(75, 221, 255, .3);
    box-shadow: inset 0 0 30px rgba(75, 221, 255, .2);
    border: 1px solid #4bddff;

    &.mask {
        bottom: auto;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
    }
}

.analysis-info {
    position: fixed;
    top: 56px;
    left: 40px;
    background-color: rgba(75, 221, 255, .3);
    box-shadow: inset 0 0 30px rgba(75, 221, 255, .2);
    border: 1px solid #4bddff;
    padding: 18px 6px;
    line-height: 1;

    .analysis-title {
        color: #fff;
        font-size: 16px;
    }

    .analysis-data {
        font-size: 28px;
        margin-top: 6px;
        color: #ffe65a;
    }
}

.container-main-info {
    padding: 8px;
}

.container-img {
    width: 48px;
    height: 48px;
}

.container-box {
    padding: 0 8px 0 0;
    font-size: 18px;
    color: #fff;
    font-weight: bold;
    line-height: 1;
}

.container-base-info {
    margin-top: 2px;
}

.import-tag {
    font-size: 14px;
    background-color: #f66d2a;
    padding: 0 6px;
}

.inside-tag {
    font-size: 14px;
    background-color: #7e9d02;
    padding: 0 6px;
    margin-left: 8px;
}

.pack-tag {
    font-size: 14px;
    background-color: #3893e2;
    padding: 0 6px;
    margin-left: 8px;
}

.action-tag {
    font-size: 14px;
    background-color: #a615c4;
    padding: 0 6px;
    margin-left: 8px;
}

.used-tag {
    font-size: 14px;
    background-color: #d72b61;
    padding: 0 6px;
    margin-left: 8px;
}

.check-tag {
    font-size: 14px;
    background-color: #ab0309;
    padding: 0 6px;
    margin-left: 8px;
}

.bind-tag {
    font-size: 14px;
    background-color: #089d8c;
    padding: 0 6px;
    margin-left: 8px;
}

.book-tag {
    font-size: 14px;
    background-color: #29a407;
    padding: 0 6px;
    margin-left: 8px;
}

.assign-tag {
    font-size: 14px;
    background-color: #8c7e04;
    padding: 0 6px;
    margin-left: 8px;
}

.block-tag {
    font-size: 14px;
    background-color: #019f4f;
    padding: 0 6px;
    margin-left: 8px;
}

.tag-wrp {
    margin-top: 4px;
}

.detail-info {
    border-top: 1px solid #4bddff;
    padding: 8px;
    color: #fff;
    font-size: 16px;
    font-weight: bold;
    position: relative;
}

.detail-label {
    text-align: right;
}

.detail-text {
}

.next-container {
    position: absolute;
    width: 48px;
    height: 48px;
    line-height: 48px;
    cursor: pointer;
    text-align: center;
    background-color: #4bddff;
    color: #fff;
    font-size: 24px;
    border-radius: 50%;
    right: 16px;
    bottom: 16px;
}

.goods-box {
    padding: 4px 6px;
    background-color: rgba(#4bddff, 0.6);
    margin-bottom: 8px;

    &:last-child {
        margin-bottom: 0;
    }
}

.detail-title {
    padding-left: 4px;
    border-left: 4px solid #4bddff;
    margin-bottom: 8px;
    line-height: 1.2;
}

.info-space {
    border-bottom: 1px solid #4bddff;
    padding: 4px;

    &:last-child {
        border-bottom: 0;
    }
}

.data-row {
    padding: 0 12px;
    width: 190px;
    border-right: 1px solid #4bddff;

    &:last-child {
        border-right: 0;
    }
}

.container-mask {
    position: fixed;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.6);
    z-index: 4;
}

.current-time {
    position: absolute;
    color: #fff;
    margin-top: -44px;
    font-weight: bold;
}
</style>
