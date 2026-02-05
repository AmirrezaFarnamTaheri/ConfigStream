import 'dart:io' show Platform;

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import 'domain_checker_controller.dart';

class DomainCheckerScreen extends StatelessWidget {
  const DomainCheckerScreen({super.key});

  bool get _isDesktop => Platform.isLinux || Platform.isWindows || Platform.isMacOS;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Domain Checker'),
        actions: [
          Consumer<DomainCheckerController>(
            builder: (context, controller, _) {
              if (controller.checkedCount > 0 && !controller.isChecking) {
                return IconButton(
                  icon: const Icon(Icons.refresh),
                  tooltip: 'Reset results',
                  onPressed: controller.resetResults,
                );
              }
              return const SizedBox.shrink();
            },
          ),
        ],
      ),
      body: Consumer<DomainCheckerController>(
        builder: (context, controller, _) {
          if (controller.isLoading) {
            return const Center(
              child: CircularProgressIndicator(),
            );
          }

          return Column(
            children: [
              // Progress and stats bar
              if (controller.isChecking || controller.checkedCount > 0)
                _buildProgressBar(context, controller),
              
              // Domain list
              Expanded(
                child: _isDesktop 
                    ? _buildDesktopLayout(context, controller)
                    : _buildMobileLayout(context, controller),
              ),
            ],
          );
        },
      ),
      floatingActionButton: Consumer<DomainCheckerController>(
        builder: (context, controller, _) {
          return Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Add domain FAB
              FloatingActionButton.small(
                heroTag: 'add_domain',
                onPressed: () => _showAddDomainDialog(context),
                child: const Icon(Icons.add),
              ).animate().fadeIn(delay: 200.ms).scale(delay: 200.ms),
              const SizedBox(width: 12),
              // Check all FAB
              FloatingActionButton.extended(
                heroTag: 'check_all',
                onPressed: controller.isChecking 
                    ? controller.stopChecking 
                    : controller.checkAll,
                icon: Icon(controller.isChecking ? Icons.stop : Icons.play_arrow),
                label: Text(controller.isChecking ? 'Stop' : 'Check All'),
              ).animate().fadeIn(delay: 100.ms).scale(delay: 100.ms),
            ],
          );
        },
      ),
    );
  }

  Widget _buildProgressBar(BuildContext context, DomainCheckerController controller) {
    final colorScheme = Theme.of(context).colorScheme;
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainerLow,
        border: Border(
          bottom: BorderSide(color: colorScheme.outlineVariant.withValues(alpha: 0.5)),
        ),
      ),
      child: Row(
        children: [
          // Progress indicator
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: controller.isChecking ? controller.progress : 1.0,
                minHeight: 6,
                backgroundColor: colorScheme.surfaceContainerHighest,
              ),
            ),
          ),
          const SizedBox(width: 20),
          // Stats row
          _buildStatChip(
            context,
            icon: Icons.check_circle,
            label: '${controller.successCount}',
            color: colorScheme.success,
          ),
          const SizedBox(width: 16),
          _buildStatChip(
            context,
            icon: Icons.cancel,
            label: '${controller.failureCount}',
            color: colorScheme.error,
          ),
          const SizedBox(width: 16),
          _buildStatChip(
            context,
            icon: Icons.pending,
            label: '${controller.totalCount - controller.checkedCount}',
            color: colorScheme.outline,
          ),
        ],
      ),
    ).animate().fadeIn().slideY(begin: -0.2, end: 0);
  }

  Widget _buildStatChip(
    BuildContext context, {
    required IconData icon,
    required String label,
    required Color color,
  }) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 16, color: color),
        const SizedBox(width: 4),
        Text(
          label,
          style: TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w600,
            color: color,
          ),
        ),
      ],
    );
  }

  Widget _buildDesktopLayout(BuildContext context, DomainCheckerController controller) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [
          for (int i = 0; i < controller.domains.length; i++)
            _DomainChip(
              domain: controller.domains[i],
              index: i,
              onTap: () => controller.checkSingle(controller.domains[i].domain),
              onDelete: controller.domains[i].isDefault 
                  ? null 
                  : () => controller.removeDomain(controller.domains[i].domain),
            ),
        ],
      ),
    );
  }

  Widget _buildMobileLayout(BuildContext context, DomainCheckerController controller) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final crossAxisCount = constraints.maxWidth < 400 ? 2 : 3;
        
        return GridView.builder(
          padding: const EdgeInsets.only(bottom: 80, top: 8, left: 8, right: 8),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: crossAxisCount,
            childAspectRatio: 1.4,
            crossAxisSpacing: 8,
            mainAxisSpacing: 8,
          ),
          itemCount: controller.domains.length,
          itemBuilder: (context, index) {
            final domain = controller.domains[index];
            return _DomainGridItem(
              domain: domain,
              index: index,
              onTap: () => controller.checkSingle(domain.domain),
              onDelete: domain.isDefault 
                  ? null 
                  : () => controller.removeDomain(domain.domain),
            );
          },
        );
      },
    );
  }

  void _showAddDomainDialog(BuildContext context) {
    final controller = context.read<DomainCheckerController>();
    final textController = TextEditingController();
    
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Add Domain'),
          content: TextField(
            controller: textController,
            autofocus: true,
            decoration: const InputDecoration(
              hintText: 'example.com',
              prefixIcon: Icon(Icons.language),
            ),
            onSubmitted: (value) {
              if (value.isNotEmpty) {
                controller.addDomain(value);
                Navigator.of(context).pop();
              }
            },
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () {
                if (textController.text.isNotEmpty) {
                  controller.addDomain(textController.text);
                  Navigator.of(context).pop();
                }
              },
              child: const Text('Add'),
            ),
          ],
        );
      },
    );
  }
}

/// Compact chip design for desktop
class _DomainChip extends StatelessWidget {
  final DomainCheckState domain;
  final int index;
  final VoidCallback onTap;
  final VoidCallback? onDelete;

  const _DomainChip({
    required this.domain,
    required this.index,
    required this.onTap,
    this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    
    final (bgColor, borderColor) = switch (domain.status) {
      CheckStatus.success => (
        colorScheme.success.withValues(alpha: 0.15),
        colorScheme.success.withValues(alpha: 0.4),
      ),
      CheckStatus.failure => (
        colorScheme.error.withValues(alpha: 0.15),
        colorScheme.error.withValues(alpha: 0.4),
      ),
      CheckStatus.checking => (
        colorScheme.primary.withValues(alpha: 0.1),
        colorScheme.primary.withValues(alpha: 0.3),
      ),
      CheckStatus.idle => (
        colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
        colorScheme.outlineVariant.withValues(alpha: 0.5),
      ),
    };

    return Material(
      color: bgColor,
      borderRadius: BorderRadius.circular(8),
      child: InkWell(
        onTap: onTap,
        onLongPress: onDelete,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: borderColor, width: 1),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              _buildStatusIndicator(colorScheme),
              const SizedBox(width: 8),
              Text(
                domain.domain,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                  color: colorScheme.onSurface,
                ),
              ),
              if (domain.status == CheckStatus.success && domain.result?.responseTimeMs != null) ...[
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: colorScheme.success.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    '${domain.result!.responseTimeMs}ms',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: colorScheme.success,
                    ),
                  ),
                ),
              ],
              if (!domain.isDefault) ...[
                const SizedBox(width: 6),
                Icon(
                  Icons.star,
                  size: 12,
                  color: colorScheme.tertiary.withValues(alpha: 0.7),
                ),
              ],
            ],
          ),
        ),
      ),
    ).animate()
        .fadeIn(delay: Duration(milliseconds: 10 * (index % 50)))
        .slideX(begin: 0.05, end: 0, delay: Duration(milliseconds: 10 * (index % 50)));
  }

  Widget _buildStatusIndicator(ColorScheme colorScheme) {
    const double size = 16;
    
    return switch (domain.status) {
      CheckStatus.idle => Icon(
        Icons.circle_outlined,
        color: colorScheme.outline,
        size: size,
      ),
      CheckStatus.checking => SizedBox(
        width: size,
        height: size,
        child: const CircularProgressIndicator(strokeWidth: 2),
      ),
      CheckStatus.success => Icon(
        Icons.check_circle,
        color: colorScheme.success,
        size: size,
      ),
      CheckStatus.failure => Icon(
        Icons.cancel,
        color: colorScheme.error,
        size: size,
      ),
    };
  }
}

/// Card design for mobile
class _DomainGridItem extends StatelessWidget {
  final DomainCheckState domain;
  final int index;
  final VoidCallback onTap;
  final VoidCallback? onDelete;

  const _DomainGridItem({
    required this.domain,
    required this.index,
    required this.onTap,
    this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    
    final cardColor = switch (domain.status) {
      CheckStatus.success => colorScheme.success.withValues(alpha: 0.15),
      CheckStatus.failure => colorScheme.error.withValues(alpha: 0.15),
      _ => null,
    };
    
    return Card(
      color: cardColor,
      child: InkWell(
        onTap: onTap,
        onLongPress: onDelete,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(10),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              _buildStatusIcon(colorScheme),
              const SizedBox(height: 6),
              Text(
                domain.domain,
                style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w500,
                ),
                textAlign: TextAlign.center,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              if (domain.status == CheckStatus.success && domain.result?.responseTimeMs != null) ...[
                const Spacer(),
                Text(
                  '${domain.result!.responseTimeMs}ms',
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                    color: colorScheme.success,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    )
        .animate()
        .fadeIn(delay: Duration(milliseconds: 15 * (index % 30)))
        .scale(begin: const Offset(0.9, 0.9), end: const Offset(1, 1), delay: Duration(milliseconds: 15 * (index % 30)));
  }

  Widget _buildStatusIcon(ColorScheme colorScheme) {
    const double iconSize = 24;
    
    return switch (domain.status) {
      CheckStatus.idle => Icon(
        Icons.circle_outlined,
        color: colorScheme.outline,
        size: iconSize,
      ),
      CheckStatus.checking => SizedBox(
        width: iconSize,
        height: iconSize,
        child: const Padding(
          padding: EdgeInsets.all(2),
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
      ),
      CheckStatus.success => Icon(
        Icons.check_circle,
        color: colorScheme.success,
        size: iconSize,
      ),
      CheckStatus.failure => Icon(
        Icons.cancel,
        color: colorScheme.error,
        size: iconSize,
      ),
    };
  }
}
