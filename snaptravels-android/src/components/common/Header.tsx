import React from 'react';
import {View, Text, TouchableOpacity, StyleSheet, StatusBar} from 'react-native';
import {useNavigation} from '@react-navigation/native';

interface HeaderProps {
  title: string;
  showBack?: boolean;
  rightComponent?: React.ReactNode;
  dark?: boolean;
}

export default function Header({title, showBack = true, rightComponent, dark = false}: HeaderProps) {
  const navigation = useNavigation();
  return (
    <View style={[styles.header, dark && styles.headerDark]}>
      <StatusBar barStyle={dark ? 'light-content' : 'dark-content'} />
      {showBack ? (
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn} hitSlop={{top: 10, bottom: 10, left: 10, right: 10}}>
          <Text style={[styles.backArrow, dark && styles.lightText]}>{'←'}</Text>
        </TouchableOpacity>
      ) : (
        <View style={styles.backBtn} />
      )}
      <Text style={[styles.title, dark && styles.lightText]} numberOfLines={1}>{title}</Text>
      <View style={styles.right}>{rightComponent}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 12,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#f1f5f9',
  },
  headerDark: {backgroundColor: '#0f172a', borderBottomColor: '#1e293b'},
  backBtn: {width: 36},
  backArrow: {fontSize: 22, color: '#1e293b'},
  lightText: {color: '#fff'},
  title: {flex: 1, fontSize: 17, fontWeight: '700', color: '#1e293b', textAlign: 'center'},
  right: {width: 36, alignItems: 'flex-end'},
});
