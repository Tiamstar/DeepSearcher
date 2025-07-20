import { FULL_PERCENT, IMAGE_PREVIEW_SWIPER_CONTROLLER } from '../common/CommonUtil'
import { ImagePreviewConfig } from '../common/ExportModel'
import { ImagePreviewSwiperConfig } from '../image_preview_swiper/ImagePreviewSwiperConfig'
import { ImagePreviewGesture } from './ImagePreviewGesture'
import { ImagePreviewState } from './ImagePreviewState'
import { ImagePreviewViewModel } from './ImagePreviewViewModel'

/**
 * 日期：2025/6/7
 */
@ComponentV2
export struct ImagePreview {
  @Param config: ImagePreviewConfig | undefined = undefined
  @Consumer(IMAGE_PREVIEW_SWIPER_CONTROLLER) private readonly swiperConfig: ImagePreviewSwiperConfig =
    new ImagePreviewSwiperConfig(undefined, this.config)
  @BuilderParam imageBuilder: CustomBuilder
  private readonly state: ImagePreviewState = new ImagePreviewState(this.getUIContext())
  private readonly viewModel: ImagePreviewViewModel =
    new ImagePreviewViewModel(this.getUIContext(), this.state, this.swiperConfig)
  private readonly imagePreviewGesture: ImagePreviewGesture = new ImagePreviewGesture({
    onDoubleClick: this.viewModel.onDoubleClick,
    onPinchStart: this.viewModel.onPinchStart,
    onPinchUpdate: this.viewModel.onPinchUpdate,
    onPinchEnd: this.viewModel.onPinchEnd,
    onPanStart: this.viewModel.onPanStart,
    onPanUpdate: this.viewModel.onPanUpdate,
    onPanEnd: this.viewModel.onPanEnd,
    onLongPress: this.viewModel.onLongPress,
    onSingleClick: this.viewModel.onClick
  })

  build() {
    if (this.imageBuilder) {
      ListItem() {
        Stack() {
          Stack() {
            this.imageBuilder()
          }
          .onAreaChange((_, area) => {
            this.state.imageWidth = area.width as number
            this.state.imageHeight = area.height as number
          })
          .scale({ x: this.state.scale, y: this.state.scale })
          .translate({ x: this.state.offsetX, y: this.state.offsetY })
        }
        .backgroundColor(this.config?.backgroundColor)
        .clip(true)
        .gestureModifier(this.imagePreviewGesture)
        .width(FULL_PERCENT)
        .height(FULL_PERCENT)
        .onVisibleAreaChange([0, 1], (isExpanding: boolean, ration: number) => {
          if (!isExpanding && ration <= 0) {
            this.viewModel.reset()
          }
        })
        .onAreaChange((_, area) => {
          this.state.previewWidth = area.width as number
          this.state.previewHeight = area.height as number
        })
      }
    }
  }
}
