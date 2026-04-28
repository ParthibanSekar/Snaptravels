import React, {forwardRef} from 'react';
import {View, TextInput, Text, StyleSheet, TextInputProps, ViewStyle} from 'react-native';

interface InputProps extends TextInputProps {
  label?: string;
  error?: string;
  containerStyle?: ViewStyle;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const Input = forwardRef<TextInput, InputProps>(
  ({label, error, containerStyle, leftIcon, rightIcon, style, ...props}, ref) => {
    return (
      <View style={[styles.container, containerStyle]}>
        {label ? <Text style={styles.label}>{label}</Text> : null}
        <View style={[styles.inputRow, error ? styles.inputError : null]}>
          {leftIcon ? <View style={styles.icon}>{leftIcon}</View> : null}
          <TextInput
            ref={ref}
            style={[styles.input, style]}
            placeholderTextColor="#94a3b8"
            {...props}
          />
          {rightIcon ? <View style={styles.icon}>{rightIcon}</View> : null}
        </View>
        {error ? <Text style={styles.errorText}>{error}</Text> : null}
      </View>
    );
  },
);

Input.displayName = 'Input';
export default Input;

const styles = StyleSheet.create({
  container: {marginBottom: 16},
  label: {fontSize: 13, fontWeight: '600', color: '#374151', marginBottom: 6},
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f8fafc',
    borderWidth: 1.5,
    borderColor: '#e2e8f0',
    borderRadius: 10,
    paddingHorizontal: 12,
    height: 48,
  },
  inputError: {borderColor: '#ef4444'},
  input: {flex: 1, fontSize: 15, color: '#1e293b', paddingVertical: 0},
  icon: {marginHorizontal: 4},
  errorText: {fontSize: 12, color: '#ef4444', marginTop: 4},
});
