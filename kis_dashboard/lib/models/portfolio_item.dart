class PortfolioItem {
  final String code;
  final String name;
  final int quantity;
  final double avgPrice;
  final double currentPrice;
  final double pnl;
  final double pnlPercent;
  final double totalValue;

  PortfolioItem({
    required this.code,
    required this.name,
    required this.quantity,
    required this.avgPrice,
    required this.currentPrice,
    required this.pnl,
    required this.pnlPercent,
    required this.totalValue,
  });

  factory PortfolioItem.fromFirestore(Map<String, dynamic> data, String id) {
    final quantity = data['quantity'] ?? 0;
    final avgPrice = (data['avgPrice'] ?? 0).toDouble();
    final currentPrice = (data['currentPrice'] ?? 0).toDouble();
    final totalValue = quantity * currentPrice;
    final pnl = (currentPrice - avgPrice) * quantity;
    final pnlPercent = avgPrice > 0 ? ((currentPrice - avgPrice) / avgPrice) * 100 : 0;

    return PortfolioItem(
      code: id,
      name: data['name'] ?? '',
      quantity: quantity,
      avgPrice: avgPrice,
      currentPrice: currentPrice,
      pnl: pnl,
      pnlPercent: pnlPercent,
      totalValue: totalValue,
    );
  }
}