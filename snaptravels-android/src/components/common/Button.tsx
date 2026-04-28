import React from 'react';
import {TouchableOpacity, Text, ActivityIndicator, StyleSheet, ViewStyle, TextStyle} from 'react-native';

interface ButtonProps {
  title: string;
  onPress: () => void;
  loading?: boolean;
  disabled?: boolean;
  variant?: 'primary' | 'secondary' | 'outline' | 'danger';
  style?: ViewStyle;
  textStyle?: TextStyle;
}

export default function Button({title, onPress, loading, disabled, variant = 'primary', style, textStyle}: ButtonProps) {
  const isDisabled = disabled || loading;
  return (
    <TouchableOpacity
      style={[styles.base, styles[variant], isDisabled && styles.disabled, style]}
      onPress={onPress}
      disabled={isDisabled}
      activeOpacity={0.8}>
      {loading ? (
        <ActivityIndicator color={variant === 'outline' ? '#6366f1' : '#fff'} size="small" />
      ) : (
        <Text style={[styles.text, styles[`${variant}Text` as keyof typeof styles] as TextStyle, textStyle]}>
          {title}
        </Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  base: {height: 50, borderRadius: 12, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 24},
  primary: {backgroundColor: '#6366f1'},
  secondary: {backgroundColor: '#f1f5f9'},
  outline: {backgroundColor: 'transparent', borderWidth: 1.5, borderColor: '#6366f1'},
  danger: {backgroundColor: '#ef4444'},
  disabled: {opacity: 0.5},
  text: {fontSize: 15, fontWeight: '600'},
  primaryText: {color: '#fff'},
  secondaryText: {color: '#1e293b'},
  outlineText: {color: '#6366f1'},
  dangerText: {color: '#fff'},
});
