import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../providers/market_data_provider.dart';
import '../theme/app_theme.dart';

class HeaderWidget extends StatelessWidget {
  const HeaderWidget({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<MarketDataProvider>(
      builder: (context, provider, child) {
        final formatter = NumberFormat('#,###');
        final isProfit = provider.todayPnL >= 0;

        return Container(
          height: 80,
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.2),
                blurRadius: 4,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          child: Row(
            children: [
              // 로고 및 타이틀
              Row(
                children: [
                  Icon(
                    Icons.trending_up,
                    color: AppTheme.successColor,
                    size: 32,
                  ),
                  const SizedBox(width: 12),
                  Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'KIS Auto Trader',
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      Text(
                        '모의투자 모드',
                        style: TextStyle(
                          fontSize: 12,
                          color: AppTheme.warningColor,
                        ),
                      ),
                    ],
                  ),
                ],
              ),

              const Spacer(),

              // 총 자산
              _buildInfoCard(
                context,
                '총 자산',
                '₩${formatter.format(provider.totalAssets)}',
                Colors.white,
              ),

              const SizedBox(width: 24),

              // 예수금
              _buildInfoCard(
                context,
                '예수금',
                '₩${formatter.format(provider.totalCash)}',
                Colors.white70,
              ),

              const SizedBox(width: 24),

              // 오늘 손익
              _buildInfoCard(
                context,
                '오늘 손익',
                '₩${formatter.format(provider.todayPnL.abs())}',
                isProfit ? AppTheme.upColor : AppTheme.downColor,
                subtitle: '${isProfit ? '+' : ''}${provider.todayPnLPercent.toStringAsFixed(2)}%',
              ),

              const SizedBox(width: 32),

              // 봇 상태
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                  color: provider.botRunning
                    ? AppTheme.successColor.withOpacity(0.2)
                    : Colors.grey.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: provider.botRunning
                      ? AppTheme.successColor
                      : Colors.grey,
                    width: 1,
                  ),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: provider.botRunning
                          ? AppTheme.successColor
                          : Colors.grey,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      provider.botRunning ? 'Running' : 'Stopped',
                      style: TextStyle(
                        color: provider.botRunning
                          ? AppTheme.successColor
                          : Colors.grey,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(width: 16),

              // 봇 제어 버튼
              ElevatedButton.icon(
                onPressed: provider.toggleBot,
                icon: Icon(provider.botRunning ? Icons.pause : Icons.play_arrow),
                label: Text(provider.botRunning ? '정지' : '시작'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: provider.botRunning
                    ? Colors.orange
                    : AppTheme.successColor,
                ),
              ),

              const SizedBox(width: 16),

              // 패닉 버튼
              ElevatedButton.icon(
                onPressed: () => _showPanicDialog(context, provider),
                icon: const Icon(Icons.warning),
                label: const Text('전량 매도'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.upColor,
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildInfoCard(
    BuildContext context,
    String label,
    String value,
    Color valueColor,
    {String? subtitle}
  ) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Colors.white54,
          ),
        ),
        Row(
          crossAxisAlignment: CrossAxisAlignment.baseline,
          textBaseline: TextBaseline.alphabetic,
          children: [
            Text(
              value,
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: valueColor,
              ),
            ),
            if (subtitle != null) ...[
              const SizedBox(width: 8),
              Text(
                subtitle,
                style: TextStyle(
                  fontSize: 14,
                  color: valueColor.withOpacity(0.8),
                ),
              ),
            ],
          ],
        ),
      ],
    );
  }

  void _showPanicDialog(BuildContext context, MarketDataProvider provider) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: Theme.of(context).colorScheme.surface,
        title: const Text('⚠️ 전량 매도 확인'),
        content: const Text('정말로 모든 포지션을 즉시 매도하시겠습니까?\n이 작업은 취소할 수 없습니다.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('취소'),
          ),
          ElevatedButton(
            onPressed: () {
              provider.panicSell();
              Navigator.of(context).pop();
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('전량 매도 명령이 전송되었습니다'),
                  backgroundColor: Colors.orange,
                ),
              );
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.upColor,
            ),
            child: const Text('전량 매도'),
          ),
        ],
      ),
    );
  }
}