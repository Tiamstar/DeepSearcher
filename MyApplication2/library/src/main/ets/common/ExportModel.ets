/**
 * 日期：2025/6/7
 */

@ObservedV2
export class ImagePreviewConfig {
  /**
   * 列表滚动器，私有
   */
  private _listScroller: ListScroller | undefined;
  /**
   * 双击缩放比例
   */
  private _doubleClickDefaultScale: number = 2;
  /**
   * 最大缩放比例
   * @returns
   */
  private _maxScale: number = 4;
  /**
   * 最小缩放比例
   * @returns
   */
  private _minScale: number = 1;
  /**
   * 长按事件
   */
  private _onLongPress?: ((index: number, event: GestureEvent) => void) | undefined;
  /**
   * 单击事件
   */
  private _onClick?: ((index: number, event: GestureEvent) => void) | undefined;
  /**
   * 指示器样式
   */
  @Trace private _indicatorStyle?: DotIndicator | DigitIndicator | undefined;
  /**
   * 指示器数量
   */
  @Trace private _indicatorCount: number = 2;
  /**
   * 初始位置
   */
  private _initialIndex: number = 0;
  /**
   * 滚动监听
   */
  private _onScrollIndex?: (start: number, end: number, center: number) => void;
  /**
   * 背景颜色
   */
  @Trace private _backgroundColor?: Color | undefined = undefined;
  /**
   * 是否展示指示器
   */
  @Trace private _showIndicator: boolean = true;
  /**
   * List缓存数量
   */
  private _cachedCount?: number | undefined;

  public get cachedCount(): number | undefined {
    return this._cachedCount;
  }

  public get showIndicator(): boolean {
    return this._showIndicator;
  }

  public get backgroundColor(): Color | undefined {
    return this._backgroundColor;
  }

  public get onScrollIndex(): ((start: number, end: number, center: number) => void) | undefined {
    return this._onScrollIndex;
  }

  public set listScroller(value: ListScroller | undefined) {
    this._listScroller = value;
  }

  public get initialIndex(): number {
    return this._initialIndex;
  }

  public get indicatorCount(): number {
    return this._indicatorCount;
  }

  public get indicatorStyle(): DotIndicator | DigitIndicator | undefined {
    return this._indicatorStyle;
  }

  public get onClick(): ((index: number, event: GestureEvent) => void) | undefined {
    return this._onClick;
  }

  public get onLongPress(): ((index: number, event: GestureEvent) => void) | undefined {
    return this._onLongPress;
  }

  public get doubleClickDefaultScale(): number { return this._doubleClickDefaultScale; }

  public get maxScale(): number { return this._maxScale; }

  public get minScale(): number {
    return this._minScale
  }

  public setDoubleClickDefaultScale(value: number): ImagePreviewConfig {
    this._doubleClickDefaultScale = value;
    return this;
  }

  public setMaxScale(value: number): ImagePreviewConfig {
    this._maxScale = value;
    return this;
  }

  public setMinScale(value: number): ImagePreviewConfig {
    this._minScale = value;
    return this;
  }

  public setOnLongPress(value: (index: number, event: GestureEvent) => void): ImagePreviewConfig {
    this._onLongPress = value;
    return this;
  }

  public setOnClick(value: (index: number, event: GestureEvent) => void): ImagePreviewConfig {
    this._onClick = value;
    return this;
  }

  public setIndicatorStyle(value: DotIndicator | DigitIndicator): ImagePreviewConfig {
    this._indicatorStyle = value;
    return this;
  }

  public setIndicatorCount(value: number): ImagePreviewConfig {
    this._indicatorCount = value;
    return this;
  }

  public setInitialIndex(value: number): ImagePreviewConfig {
    this._initialIndex = value;
    return this;
  }

  public setOnScrollIndex(value: (start: number, end: number, center: number) => void): ImagePreviewConfig {
    this._onScrollIndex = value;
    return this;
  }

  public setBackgroundColor(value: Color): ImagePreviewConfig {
    this._backgroundColor = value;
    return this;
  }

  public setShowIndicator(value: boolean): ImagePreviewConfig {
    this._showIndicator = value;
    return this;
  }

  public setCachedCount(value: number): ImagePreviewConfig {
    this._cachedCount = value;
    return this;
  }

  /**
   * 下一页
   */
  public nextPage(animation: boolean = true): void {
    this._listScroller?.scrollPage({ next: true, animation: animation })
  }

  /**
   * 上一页
   */
  public prevPage(animation: boolean = true): void {
    this._listScroller?.scrollPage({ next: false, animation: animation })
  }

  /**
   * 滚动到指定页
   * @param index 页码
   * @param smooth 是否有动效
   */
  public scrollToIndex(index: number, smooth: boolean = true): void {
    this._listScroller?.scrollToIndex(index, smooth,)
  }
}