class StockItem {
  final String code;
  final String name;
  final double currentPrice;
  final double changePercent;
  final double volume;
  final double volumeChange;
  final double rsi;
  final double mfi;
  final bool nearBuySignal;

  StockItem({
    required this.code,
    required this.name,
    required this.currentPrice,
    required this.changePercent,
    required this.volume,
    required this.volumeChange,
    required this.rsi,
    required this.mfi,
    required this.nearBuySignal,
  });

  factory StockItem.fromFirestore(Map<String, dynamic> data, String id) {
    return StockItem(
      code: id,
      name: data['name'] ?? '',
      currentPrice: (data['currentPrice'] ?? 0).toDouble(),
      changePercent: (data['changePercent'] ?? 0).toDouble(),
      volume: (data['volume'] ?? 0).toDouble(),
      volumeChange: (data['volumeChange'] ?? 0).toDouble(),
      rsi: (data['rsi'] ?? 50).toDouble(),
      mfi: (data['mfi'] ?? 50).toDouble(),
      nearBuySignal: data['nearBuySignal'] ?? false,
    );
  }
}