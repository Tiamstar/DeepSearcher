/**
 * 日期：2025/6/7
 */
export class ImagePreviewGesture implements GestureModifier {
  private readonly option: ImagePreviewGestureOption
  private gestureEvent?: UIGestureEvent
  private readonly gestureHandler: GestureGroupHandler

  constructor(option: ImagePreviewGestureOption) {
    this.option = option
    this.gestureHandler = new GestureGroupHandler({
      mode: GestureMode.Exclusive,
      gestures: [
      // 缩放
        new PinchGestureHandler()
          .tag(ImagePreviewGestureTag.Pinch)
          .onActionStart(this.option.onPinchStart)
          .onActionUpdate(this.option.onPinchUpdate)
          .onActionEnd(this.option.onPinchEnd),
        // 平移
        new PanGestureHandler()
          .tag(ImagePreviewGestureTag.Pan)
          .onActionStart(this.option.onPanStart)
          .onActionUpdate(this.option.onPanUpdate)
          .onActionEnd(this.option.onPanEnd),
        // 长按
        new LongPressGestureHandler()
          .tag(ImagePreviewGestureTag.LongPress)
          .onAction(this.option.onLongPress),
        // 双击
        new TapGestureHandler({ count: 2 })
          .tag(ImagePreviewGestureTag.DoubleClick)
          .onAction(this.option.onDoubleClick),
        // 单击
        new TapGestureHandler()
          .tag(ImagePreviewGestureTag.SingleClick)
          .onAction(this.option.onSingleClick)
      ]
    })
  }

  applyGesture(event: UIGestureEvent): void {
    this.gestureEvent = event
    this.resetGesture()
  }

  // 重置
  resetGesture(): void {
    this.gestureEvent?.addGesture(this.gestureHandler)
  }

}


interface ImagePreviewGestureOption {
  onDoubleClick?: Callback<GestureEvent>
  onPinchStart?: Callback<GestureEvent>
  onPinchUpdate?: Callback<GestureEvent>
  onPinchEnd?: Callback<GestureEvent>
  onPanStart?: Callback<GestureEvent>
  onPanUpdate?: Callback<GestureEvent>
  onPanEnd?: Callback<GestureEvent>
  onLongPress?: Callback<GestureEvent>
  onSingleClick?: Callback<GestureEvent>
}


enum ImagePreviewGestureTag {
  DoubleClick = "DoubleClick",
  SingleClick = "SingleClick",
  LongPress = "LongPress",
  Pan = "Pan",
  Pinch = "Pinch",
  // Rotate = "Rotate",
}