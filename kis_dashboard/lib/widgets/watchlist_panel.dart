import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/market_data_provider.dart';
import '../theme/app_theme.dart';
import '../models/stock_item.dart';

class WatchlistPanel extends StatelessWidget {
  const WatchlistPanel({super.key});

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
                const Icon(Icons.remove_red_eye, size: 20),
                const SizedBox(width: 8),
                const Text(
                  '감시 종목',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const Spacer(),
                Consumer<MarketDataProvider>(
                  builder: (context, provider, _) {
                    return Text(
                      '${provider.watchlist.length}개',
                      style: TextStyle(
                        color: AppTheme.successColor,
                        fontWeight: FontWeight.bold,
                      ),
                    );
                  },
                ),
              ],
            ),
          ),

          // 테이블 헤더
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            decoration: BoxDecoration(
              color: Colors.black.withOpacity(0.3),
            ),
            child: Row(
              children: [
                Expanded(flex: 3, child: Text('종목', style: _headerStyle())),
                Expanded(flex: 2, child: Text('현재가', style: _headerStyle(), textAlign: TextAlign.right)),
                Expanded(flex: 2, child: Text('등락률', style: _headerStyle(), textAlign: TextAlign.right)),
                Expanded(flex: 1, child: Text('RSI', style: _headerStyle(), textAlign: TextAlign.right)),
                Expanded(flex: 1, child: Text('MFI', style: _headerStyle(), textAlign: TextAlign.right)),
                Expanded(flex: 2, child: Text('거래량', style: _headerStyle(), textAlign: TextAlign.right)),
              ],
            ),
          ),

          // 종목 리스트
          Expanded(
            child: Consumer<MarketDataProvider>(
              builder: (context, provider, child) {
                if (provider.watchlist.isEmpty) {
                  return const Center(
                    child: Text(
                      '감시 중인 종목이 없습니다',
                      style: TextStyle(color: Colors.white54),
                    ),
                  );
                }

                return ListView.builder(
                  itemCount: provider.watchlist.length,
                  itemBuilder: (context, index) {
                    final stock = provider.watchlist[index];
                    return _buildStockRow(stock, context);
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStockRow(StockItem stock, BuildContext context) {
    final isUp = stock.changePercent > 0;
    final isDown = stock.changePercent < 0;
    final changeColor = isUp ? AppTheme.upColor : (isDown ? AppTheme.downColor : AppTheme.neutralColor);
    final shouldHighlight = stock.nearBuySignal || stock.rsi < 30;

    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      decoration: BoxDecoration(
        color: shouldHighlight
            ? AppTheme.warningColor.withOpacity(0.1)
            : Colors.transparent,
        border: Border(
          bottom: BorderSide(
            color: Theme.of(context).dividerColor.withOpacity(0.3),
          ),
        ),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () {
            // TODO: 상세 정보 표시
          },
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Row(
              children: [
                // 종목명
                Expanded(
                  flex: 3,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        stock.name,
                        style: const TextStyle(fontWeight: FontWeight.w600),
                        overflow: TextOverflow.ellipsis,
                      ),
                      Text(
                        stock.code,
                        style: TextStyle(
                          fontSize: 11,
                          color: Colors.white.withOpacity(0.5),
                        ),
                      ),
                    ],
                  ),
                ),

                // 현재가
                Expanded(
                  flex: 2,
                  child: Text(
                    _formatPrice(stock.currentPrice),
                    style: TextStyle(color: changeColor),
                    textAlign: TextAlign.right,
                  ),
                ),

                // 등락률
                Expanded(
                  flex: 2,
                  child: Container(
                    alignment: Alignment.centerRight,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: changeColor.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        '${isUp ? '+' : ''}${stock.changePercent.toStringAsFixed(2)}%',
                        style: TextStyle(
                          color: changeColor,
                          fontWeight: FontWeight.bold,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ),
                ),

                // RSI
                Expanded(
                  flex: 1,
                  child: Text(
                    stock.rsi.toStringAsFixed(0),
                    style: TextStyle(
                      color: _getRSIColor(stock.rsi),
                      fontWeight: stock.rsi < 30 ? FontWeight.bold : FontWeight.normal,
                    ),
                    textAlign: TextAlign.right,
                  ),
                ),

                // MFI
                Expanded(
                  flex: 1,
                  child: Text(
                    stock.mfi.toStringAsFixed(0),
                    style: TextStyle(
                      color: _getMFIColor(stock.mfi),
                      fontWeight: stock.mfi < 20 ? FontWeight.bold : FontWeight.normal,
                    ),
                    textAlign: TextAlign.right,
                  ),
                ),

                // 거래량 변화
                Expanded(
                  flex: 2,
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      if (stock.volumeChange > 500)
                        const Icon(Icons.local_fire_department, color: Colors.orange, size: 16),
                      Text(
                        '${stock.volumeChange.toStringAsFixed(0)}%',
                        style: TextStyle(
                          color: stock.volumeChange > 200
                              ? Colors.orange
                              : Colors.white70,
                        ),
                        textAlign: TextAlign.right,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  TextStyle _headerStyle() {
    return const TextStyle(
      fontSize: 12,
      color: Colors.white54,
      fontWeight: FontWeight.w600,
    );
  }

  String _formatPrice(double price) {
    if (price >= 1000) {
      return '${(price / 1).toStringAsFixed(0)}';
    }
    return price.toStringAsFixed(2);
  }

  Color _getRSIColor(double rsi) {
    if (rsi < 30) return AppTheme.downColor;
    if (rsi > 70) return AppTheme.upColor;
    return Colors.white70;
  }

  Color _getMFIColor(double mfi) {
    if (mfi < 20) return AppTheme.downColor;
    if (mfi > 80) return AppTheme.upColor;
    return Colors.white70;
  }
}