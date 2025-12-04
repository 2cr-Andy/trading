import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../providers/market_data_provider.dart';
import '../models/portfolio_item.dart';
import '../theme/app_theme.dart';

class PortfolioPanel extends StatelessWidget {
  const PortfolioPanel({super.key});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surface.withOpacity(0.5),
              border: Border(
                bottom: BorderSide(
                  color: Theme.of(context).dividerColor,
                ),
              ),
            ),
            child: Row(
              children: [
                const Icon(Icons.account_balance_wallet, size: 20),
                const SizedBox(width: 8),
                const Text(
                  '포트폴리오',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const Spacer(),
                Consumer<MarketDataProvider>(
                  builder: (context, provider, _) {
                    final totalValue = provider.portfolio.fold<double>(
                      0, (sum, item) => sum + item.totalValue
                    );
                    return Text(
                      '₩${NumberFormat('#,###').format(totalValue)}',
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                      ),
                    );
                  },
                ),
              ],
            ),
          ),

          Expanded(
            child: Consumer<MarketDataProvider>(
              builder: (context, provider, child) {
                if (provider.portfolio.isEmpty) {
                  return const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.inventory_2_outlined,
                          size: 48,
                          color: Colors.white24,
                        ),
                        SizedBox(height: 16),
                        Text(
                          '보유 종목이 없습니다',
                          style: TextStyle(color: Colors.white54),
                        ),
                      ],
                    ),
                  );
                }

                return GridView.builder(
                  padding: const EdgeInsets.all(16),
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2,
                    childAspectRatio: 1.5,
                    crossAxisSpacing: 16,
                    mainAxisSpacing: 16,
                  ),
                  itemCount: provider.portfolio.length,
                  itemBuilder: (context, index) {
                    return _buildPortfolioCard(
                      context,
                      provider.portfolio[index],
                      provider,
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPortfolioCard(
    BuildContext context,
    PortfolioItem item,
    MarketDataProvider provider,
  ) {
    final isProfit = item.pnlPercent >= 0;
    final color = isProfit ? AppTheme.upColor : AppTheme.downColor;
    final formatter = NumberFormat('#,###');

    return Card(
      elevation: 2,
      color: Theme.of(context).colorScheme.surface,
      child: InkWell(
        onTap: () => _showPortfolioDetail(context, item, provider),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 종목명과 수익률
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          item.name,
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 14,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                        Text(
                          item.code,
                          style: TextStyle(
                            fontSize: 11,
                            color: Colors.white.withOpacity(0.5),
                          ),
                        ),
                      ],
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: color.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      '${isProfit ? '+' : ''}${item.pnlPercent.toStringAsFixed(2)}%',
                      style: TextStyle(
                        color: color,
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                    ),
                  ),
                ],
              ),

              const Spacer(),

              // 평가금액
              Text(
                '₩${formatter.format(item.totalValue)}',
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),

              const SizedBox(height: 4),

              // 손익금액
              Row(
                children: [
                  Text(
                    '${isProfit ? '+' : ''}₩${formatter.format(item.pnl.abs())}',
                    style: TextStyle(
                      color: color,
                      fontSize: 13,
                    ),
                  ),
                  const Spacer(),
                  Text(
                    '${item.quantity}주',
                    style: TextStyle(
                      fontSize: 11,
                      color: Colors.white.withOpacity(0.5),
                    ),
                  ),
                ],
              ),

              const Spacer(),

              // 수동 매도 버튼
              SizedBox(
                width: double.infinity,
                height: 28,
                child: ElevatedButton(
                  onPressed: () => _showSellConfirmDialog(context, item, provider),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.orange.withOpacity(0.2),
                    foregroundColor: Colors.orange,
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(6),
                    ),
                  ),
                  child: const Text(
                    '수동 매도',
                    style: TextStyle(fontSize: 12),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showPortfolioDetail(
    BuildContext context,
    PortfolioItem item,
    MarketDataProvider provider,
  ) {
    final formatter = NumberFormat('#,###');

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: Theme.of(context).colorScheme.surface,
        title: Text('${item.name} (${item.code})'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildDetailRow('보유수량', '${item.quantity}주'),
            _buildDetailRow('평균단가', '₩${formatter.format(item.avgPrice)}'),
            _buildDetailRow('현재가', '₩${formatter.format(item.currentPrice)}'),
            _buildDetailRow('평가금액', '₩${formatter.format(item.totalValue)}'),
            _buildDetailRow(
              '평가손익',
              '₩${formatter.format(item.pnl)}',
              valueColor: item.pnl >= 0 ? AppTheme.upColor : AppTheme.downColor,
            ),
            _buildDetailRow(
              '수익률',
              '${item.pnlPercent >= 0 ? '+' : ''}${item.pnlPercent.toStringAsFixed(2)}%',
              valueColor: item.pnl >= 0 ? AppTheme.upColor : AppTheme.downColor,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('닫기'),
          ),
          ElevatedButton.icon(
            onPressed: () {
              Navigator.of(context).pop();
              _showSellConfirmDialog(context, item, provider);
            },
            icon: const Icon(Icons.sell),
            label: const Text('매도'),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.orange,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDetailRow(String label, String value, {Color? valueColor}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.white54)),
          Text(
            value,
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color: valueColor ?? Colors.white,
            ),
          ),
        ],
      ),
    );
  }

  void _showSellConfirmDialog(
    BuildContext context,
    PortfolioItem item,
    MarketDataProvider provider,
  ) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: Theme.of(context).colorScheme.surface,
        title: const Text('매도 확인'),
        content: Text(
          '${item.name} ${item.quantity}주를 시장가로 매도하시겠습니까?'
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('취소'),
          ),
          ElevatedButton(
            onPressed: () {
              provider.manualSell(item.code);
              Navigator.of(context).pop();
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('${item.name} 매도 주문이 전송되었습니다'),
                  backgroundColor: Colors.orange,
                ),
              );
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.orange,
            ),
            child: const Text('매도'),
          ),
        ],
      ),
    );
  }
}